"""
Replay engine - Deterministic execution of a saved CapabilityArtifact.

ReplayEngine coordinates:
1. Enforcing safety guardrails before the browser ever touches a step
2. Validating the parameters the caller supplied against the artifact's contract
3. Connecting the browser and walking the artifact's steps in order
4. Resolving "${param}" placeholders and storing "read" results as they happen
5. Handling a failed step according to the artifact's own error_handlers
   (retry / skip / business_outcome / escalate)
6. Reporting a structured ReplayResult (success / business_outcome / failed)

No LLM is involved anywhere in this file - that is the entire point of replay.
"""

import logging
from typing import Dict, Optional

from src.agent.browser import BrowserManager
from src.artifacts.schema import AutomationStep, CapabilityArtifact, ReplayResult
from src.escalation.handler import EscalationHandler
from src.escalation.intervention import HumanIntervention
from src.logging.audit import AuditLogger
from src.replay.error_policy import ErrorPolicy
from src.replay.parameter_resolver import ParameterResolver
from src.replay.step_executor import StepExecutor
from src.safety.guard import SafetyGuard
from src.safety.redaction import redact

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1


class ReplayEngine:
    """Runs a CapabilityArtifact's steps against a live browser, deterministically."""

    def __init__(
        self,
        browser_manager: BrowserManager,
        safety_guard: Optional[SafetyGuard] = None,
        escalation_handler: Optional[EscalationHandler] = None,
        human_intervention: Optional[HumanIntervention] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.browser_manager = browser_manager
        self.parameter_resolver = ParameterResolver()
        self.step_executor = StepExecutor(browser_manager)
        self.safety_guard = safety_guard or SafetyGuard()
        self.escalation_handler = escalation_handler or EscalationHandler()
        self.human_intervention = human_intervention or HumanIntervention()
        self.audit_logger = audit_logger or AuditLogger()
        self.error_policy = ErrorPolicy()

    async def run(
        self,
        artifact: CapabilityArtifact,
        target_url: str,
        params: Dict[str, str],
        headless: bool = True,
        interactive: bool = False,
    ) -> ReplayResult:
        """
        Execute every step of `artifact` in order.

        Args:
            artifact: The validated recipe to run.
            target_url: URL of the app to automate.
            params: Input parameter values referenced by the artifact's steps.
            headless: Whether to run the browser without a visible window.

        Returns:
            ReplayResult describing what happened.
        """
        self.safety_guard.check_artifact(artifact)
        self.parameter_resolver.validate_required(artifact, params)
        self.audit_logger.event("replay_started", artifact_id=artifact.id)

        # `context` holds parameter values plus anything steps "read" and
        # stored, so later steps (and final outputs) can reference them.
        context: Dict[str, str] = dict(params)
        steps_completed = 0

        try:
            await self.browser_manager.connect(target_url, headless=headless)

            for step in artifact.steps:
                self.safety_guard.check_step(step)
                logger.info(f"[{step.id}] {step.action} -> {step.target.selector}")
                self.audit_logger.event("step_started", artifact_id=artifact.id, step_id=step.id, action=step.action)

                if step.requires_human_approval:
                    if not interactive:
                        raise RuntimeError(
                            f"Step '{step.id}' requires human approval; rerun with --interactive"
                        )
                    await self.human_intervention.wait_for_operator(
                        step.human_prompt or self._approval_prompt(step)
                    )

                outcome = await self._run_step_with_recovery(
                    artifact, step, context, steps_completed, interactive
                )
                if outcome is not None:
                    # A declared error handler resolved this step's failure
                    # into a final result (business_outcome, or an escalation).
                    return outcome

                steps_completed += 1
                self.audit_logger.event("step_completed", artifact_id=artifact.id, step_id=step.id)

            outputs = {name: context.get(name, "") for name in artifact.outputs}
            logger.info(f"✅ Replay succeeded: {redact(str(outputs))}")
            self.audit_logger.event("replay_succeeded", artifact_id=artifact.id, steps_completed=steps_completed)

            return ReplayResult(
                status="success",
                outputs=outputs,
                steps_completed=steps_completed,
            )

        except Exception as exc:
            logger.error(f"❌ Replay failed after {steps_completed} step(s): {redact(str(exc))}")
            self.audit_logger.event("replay_failed", artifact_id=artifact.id, steps_completed=steps_completed, error=str(exc))
            escalation = self.escalation_handler.escalate(
                artifact_id=artifact.id,
                step=artifact.steps[steps_completed] if steps_completed < len(artifact.steps) else artifact.steps[-1],
                reason=str(exc),
            )
            return ReplayResult(
                status="failed",
                error={"message": str(exc), "escalation": escalation},
                steps_completed=steps_completed,
            )

        finally:
            await self.browser_manager.disconnect()

    async def _run_step_with_recovery(
        self,
        artifact: CapabilityArtifact,
        step: AutomationStep,
        context: Dict[str, str],
        steps_completed_before: int,
        interactive: bool,
    ) -> Optional[ReplayResult]:
        """
        Execute one step, retrying/skipping/escalating per its declared
        ErrorHandler (if any) when it fails.

        Returns:
            None if the step succeeded (or was skipped) and the run should
            continue; a ReplayResult if the failure produced a final outcome.
        """
        attempts_allowed = 1 + _MAX_RETRIES

        intervention_used = False

        for attempt in range(1, attempts_allowed + 1):
            try:
                resolved_value = (
                    self.parameter_resolver.resolve(step.value, context)
                    if step.value is not None
                    else None
                )
                extracted_text = await self.step_executor.execute(step, resolved_value)

                if step.store_as:
                    context[step.store_as] = extracted_text or ""

                return None

            except Exception as exc:
                handler = self.error_policy.resolve(artifact, step.id)

                if handler and handler.recovery_action == "retry" and attempt < attempts_allowed:
                    logger.warning(f"↻ Retrying step '{step.id}' (attempt {attempt + 1}/{attempts_allowed})")
                    continue

                if handler and handler.recovery_action == "skip":
                    logger.warning(f"⏭ Skipping step '{step.id}' after failure: {redact(str(exc))}")
                    return None

                if handler and handler.recovery_action == "business_outcome":
                    logger.info(f"ℹ️ Step '{step.id}' resolved to business outcome '{handler.result}'")
                    return ReplayResult(
                        status="business_outcome",
                        business_outcome=handler.result,
                        steps_completed=steps_completed_before,
                    )

                if interactive and not intervention_used:
                    intervention_used = True
                    action_required = self._human_action_required(step, exc)
                    self.escalation_handler.escalate(
                        artifact_id=artifact.id,
                        step=step,
                        reason=action_required,
                    )
                    await self.human_intervention.wait_for_operator(action_required)
                    continue

                # No handler, or explicit "escalate": fail safe by default.
                raise

    @staticmethod
    def _human_action_required(step: AutomationStep, error: Exception) -> str:
        """Describe the failed step and the action needed before retry."""
        target = step.target.selector or step.target.accessibility_label or "the target element"
        suggested_action = (
            "If search results are visible, open the matching member's View Details link."
            if step.action == "wait"
            else "Complete the missing browser action manually."
        )
        return (
            f"Replay paused at {step.id} ({step.description}).\n"
            f"The expected target is {target}.\n"
            f"Failure: {error}\n"
            f"Suggested action: {suggested_action}\n"
            "Resolve the issue in the open browser, then resume."
        )

    @staticmethod
    def _approval_prompt(step: AutomationStep) -> str:
        """Describe the sensitive action that needs human authorization."""
        return (
            f"Approval required before {step.id} ({step.description}).\n"
            "Complete the sensitive data entry and review it in the browser.\n"
            "Press Enter only after the value and target account are correct."
        )
