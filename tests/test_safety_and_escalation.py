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
