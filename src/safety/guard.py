"""
Safety guard - enforces a SafetyPolicy against an artifact before/while it runs.

ReplayEngine calls this before connecting the browser (whole-artifact check)
and before executing each step (per-step check), so an unsafe artifact never
gets the chance to touch a real page.
"""

import logging
from typing import Optional

from src.artifacts.schema import AutomationStep, CapabilityArtifact
from src.safety.policy import SafetyPolicy

logger = logging.getLogger(__name__)


class SafetyViolationError(Exception):
    """Raised when a step or artifact breaks a safety policy rule."""


class SafetyGuard:
    """Blocks unsafe artifacts/steps before the browser ever touches them."""

    def __init__(self, policy: Optional[SafetyPolicy] = None):
        self.policy = policy or SafetyPolicy()

    def check_artifact(self, artifact: CapabilityArtifact) -> None:
        """Reject an artifact outright if it violates run-wide limits."""
        if len(artifact.steps) > self.policy.max_steps_per_run:
            raise SafetyViolationError(
                f"Artifact '{artifact.id}' has {len(artifact.steps)} steps, "
                f"exceeding the policy limit of {self.policy.max_steps_per_run}"
            )

    def check_step(self, step: AutomationStep) -> None:
        """Reject a single step if its action is not on the allowlist."""
        if step.action not in self.policy.allowed_actions:
            logger.warning(f"🚫 Blocked step '{step.id}': action '{step.action}' not permitted")
            raise SafetyViolationError(
                f"Action '{step.action}' on step '{step.id}' is not permitted by safety policy"
            )
