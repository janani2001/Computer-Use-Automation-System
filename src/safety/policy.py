"""
Safety policy - the guardrail rules replay must enforce.

This file is intentionally pure data (no logic). `SafetyGuard` is the class
that actually enforces these rules; keeping the two separate means the
rules can be swapped/tuned without touching enforcement code.
"""

from dataclasses import dataclass, field
from typing import FrozenSet

_DEFAULT_ALLOWED_ACTIONS: FrozenSet[str] = frozenset(
    {"click", "type", "read", "wait", "submit", "navigate", "screenshot"}
)


@dataclass(frozen=True)
class SafetyPolicy:
    """Guardrail limits enforced by SafetyGuard before/while replaying."""

    # Defense in depth: artifact JSON files are semi-trusted input (they may
    # have been hand-edited or produced by an LLM). Only known-safe actions
    # from the schema are ever allowed to reach the browser.
    allowed_actions: FrozenSet[str] = field(default_factory=lambda: _DEFAULT_ALLOWED_ACTIONS)

    # Prevents a malformed or malicious artifact from running an unbounded
    # number of browser actions (a simple runaway/DoS guard).
    max_steps_per_run: int = 50
