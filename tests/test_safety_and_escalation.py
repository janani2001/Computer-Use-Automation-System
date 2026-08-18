"""Unit tests for the safety guard, redaction, escalation handler, and error policy."""

import json

import pytest

from src.artifacts.schema import (
    AutomationStep,
    CapabilityArtifact,
    ElementTarget,
    ErrorHandler,
)
from src.escalation.handler import EscalationHandler
from src.replay.error_policy import ErrorPolicy
from src.safety.guard import SafetyGuard, SafetyViolationError
from src.safety.policy import SafetyPolicy
from src.safety.redaction import redact


class _FakeIntervention:
    def __init__(self):
        self.messages = []

    async def wait_for_operator(self, action_required: str) -> None:
        self.messages.append(action_required)


class _FakeBrowser:
    async def connect(self, target_url, headless=True):
        pass

    async def disconnect(self):
        pass


def _step(step_id: str = "step_1", action: str = "click") -> AutomationStep:
    return AutomationStep(
        id=step_id,
        action=action,
        target=ElementTarget(selector="#x", type="css", description="d"),
        description="d",
    )


def _artifact(**overrides) -> CapabilityArtifact:
    defaults = dict(
        version="1.0",
        id="a1",
        name="Test artifact",
        goal="g",
        steps=[_step()],
        success_condition="ok",
    )
    defaults.update(overrides)
    return CapabilityArtifact(**defaults)


def test_safety_guard_allows_permitted_action():
    guard = SafetyGuard(SafetyPolicy())
    guard.check_step(_step(action="click"))  # should not raise


def test_safety_guard_blocks_disallowed_action():
    # "navigate" is a schema-valid action, but this policy only permits "click" -
    # this proves SafetyGuard enforces a stricter subset than the schema itself.
    guard = SafetyGuard(SafetyPolicy(allowed_actions=frozenset({"click"})))
    with pytest.raises(SafetyViolationError):
        guard.check_step(_step(action="navigate"))


def test_safety_guard_blocks_oversized_artifact():
    guard = SafetyGuard(SafetyPolicy(max_steps_per_run=1))
    artifact = _artifact(steps=[_step("step_1"), _step("step_2")])
    with pytest.raises(SafetyViolationError):
        guard.check_artifact(artifact)


def test_redact_masks_long_digit_sequences():
    assert redact("Balance for account 1234567 is $500") == "Balance for account [REDACTED] is $500"


def test_escalation_handler_writes_append_only_record(tmp_path):
    handler = EscalationHandler(log_path=tmp_path / "escalations.jsonl")

    record = handler.escalate(artifact_id="a1", step=_step(), reason="timeout waiting for selector")

    assert record["artifact_id"] == "a1"
    assert record["step_id"] == "step_1"

    lines = (tmp_path / "escalations.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["reason"] == "timeout waiting for selector"


def test_error_policy_returns_none_when_no_handler_declared():
    artifact = _artifact()
    assert ErrorPolicy().resolve(artifact, "step_1") is None


def test_error_policy_finds_declared_handler_by_step_id():
    artifact = _artifact(
        error_handlers=[
            ErrorHandler(
                step_id="step_1",
                error_type="timeout",
                recovery_action="skip",
                description="ok to skip",
            )
        ]
    )

    handler = ErrorPolicy().resolve(artifact, "step_1")

    assert handler is not None
    assert handler.recovery_action == "skip"


@pytest.mark.asyncio
async def test_interactive_replay_resumes_after_human_confirmation():
    intervention = _FakeIntervention()
    engine = __import__("src.replay.engine", fromlist=["ReplayEngine"]).ReplayEngine(
        browser_manager=object(),
        human_intervention=intervention,
    )
    attempts = []

    class _StepExecutor:
        async def execute(self, step, resolved_value):
            attempts.append(step.id)
            if len(attempts) == 1:
                raise RuntimeError("element is covered by a dialog")
            return None

    engine.step_executor = _StepExecutor()
    artifact = _artifact()

    outcome = await engine._run_step_with_recovery(
        artifact,
        artifact.steps[0],
        {},
        steps_completed_before=0,
        interactive=True,
    )

    assert outcome is None
    assert attempts == ["step_1", "step_1"]
    assert len(intervention.messages) == 1
    assert "element is covered by a dialog" in intervention.messages[0]


@pytest.mark.asyncio
async def test_approval_gate_fails_closed_without_interactive_mode():
    from src.replay.engine import ReplayEngine

    class _Browser:
        async def connect(self, target_url, headless):
            pass

        async def disconnect(self):
            pass

    artifact = _artifact(
        steps=[_step()],
    )
    artifact.steps[0].requires_human_approval = True
    engine = ReplayEngine(_Browser())

    result = await engine.run(
        artifact,
        target_url="http://test",
        params={},
        headless=True,
        interactive=False,
    )

    assert result.status == "failed"
    assert "requires human approval" in result.error["message"]


@pytest.mark.asyncio
async def test_interactive_handoff_escalates_after_operator_does_not_fix_step(tmp_path):
    from src.escalation.handler import EscalationHandler
    from src.replay.engine import ReplayEngine

    class _Browser:
        async def connect(self, target_url, headless):
            pass

        async def disconnect(self):
            pass

    class _Intervention:
        async def wait_for_operator(self, action_required):
            pass

    class _AlwaysFailingExecutor:
        async def execute(self, step, resolved_value):
            raise RuntimeError("dialog remains open")

    artifact = _artifact()
    escalation_path = tmp_path / "escalations.jsonl"
    engine = ReplayEngine(
        _Browser(),
        escalation_handler=EscalationHandler(escalation_path),
        human_intervention=_Intervention(),
    )
    engine.step_executor = _AlwaysFailingExecutor()

    result = await engine.run(
        artifact,
        target_url="http://test",
        params={},
        headless=False,
        interactive=True,
    )

    assert result.status == "failed"
    assert result.steps_completed == 0
    assert "dialog remains open" in result.error["message"]
    assert len(escalation_path.read_text().splitlines()) == 2


@pytest.mark.asyncio
async def test_approval_gate_runs_before_sensitive_step():
    intervention = _FakeIntervention()
    engine = __import__("src.replay.engine", fromlist=["ReplayEngine"]).ReplayEngine(
        browser_manager=_FakeBrowser(),
        human_intervention=intervention,
    )
    executed = []

    class _StepExecutor:
        async def execute(self, step, resolved_value):
            executed.append(step.id)
            return None

    engine.step_executor = _StepExecutor()
    artifact = _artifact(
        steps=[
            _step(),
            _step("submit_update", action="submit").model_copy(
                update={
                    "requires_human_approval": True,
                    "human_prompt": "Enter and review the new savings balance, then continue.",
                }
            ),
        ]
    )

    result = await engine.run(
        artifact,
        target_url="http://bank.test",
        params={},
        interactive=True,
    )

    assert result.status == "success"
    assert executed == ["step_1", "submit_update"]
    assert intervention.messages == [
        "Enter and review the new savings balance, then continue."
    ]
