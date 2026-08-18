"""
Step executor - Runs a single AutomationStep against a live browser.

This is the only place that maps an artifact's declarative `action` string
(e.g. "click", "type", "read") onto a concrete BrowserManager call. Adding a
new action type means adding one branch here, nowhere else.
"""

import logging
from typing import Optional

from src.agent.browser import BrowserManager
from src.artifacts.schema import AutomationStep

logger = logging.getLogger(__name__)


class UnsupportedActionError(Exception):
    """Raised when a step's action has no matching browser operation."""


class StepExecutor:
    """Executes one AutomationStep and returns any text it extracted."""

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager

    async def execute(self, step: AutomationStep, resolved_value: Optional[str]) -> Optional[str]:
        """
        Run the step's action.

        Args:
            step: The step to run (selector/timeout come from step.target).
            resolved_value: step.value with any ${param} placeholders already
                substituted (None if the step has no value).

        Returns:
            Extracted text for "read" steps, otherwise None.
        """
        selector = step.target.selector

        if step.action == "click":
            await self.browser_manager.click_target(step.target)
            return None

        if step.action == "type":
            await self.browser_manager.type_target(step.target, resolved_value or "")
            return None

        if step.action == "submit":
            await self.browser_manager.submit_form(selector)
            return None

        if step.action == "wait":
            await self.browser_manager.wait_for_target(step.target, timeout_ms=step.timeout_ms)
            return None

        if step.action == "read":
            return await self.browser_manager.read_target_text(step.target)

        if step.action == "navigate":
            await self.browser_manager.navigate(resolved_value or selector)
            return None

        if step.action == "screenshot":
            await self.browser_manager.take_screenshot()
            return None

        raise UnsupportedActionError(f"No executor registered for action '{step.action}'")
