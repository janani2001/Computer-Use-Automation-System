"""
Agent module - Main orchestration for discovery loop.

DiscoveryAgent coordinates:
1. Browser navigation and screenshots
2. Claude vision analysis
3. Schema parsing and validation
4. Artifact saving
"""

import asyncio
import logging
import json
import re
from typing import Optional
from pathlib import Path

from src.agent.browser import BrowserManager
from src.agent.vision import VisionClient
from src.agent.parser import ResponseParser
from src.artifacts.schema import CapabilityArtifact
from src.replay.parameter_resolver import ParameterResolver
from src.replay.step_executor import StepExecutor

logger = logging.getLogger(__name__)


class DiscoveryAgent:
    """
    Discovers automation flows by sending screenshots to Claude.
    
    Workflow:
    1. Start browser, navigate to target app
    2. Take screenshot
    3. Send to Claude with goal
    4. Claude describes steps needed
    5. Parse Claude response to CapabilityArtifact
    6. Save artifact as JSON
    7. Return result
    """
    
    def __init__(self, api_key: Optional[str] = None, headless: bool = True):
        """
        Initialize discovery agent.
        
        Args:
            api_key: Anthropic API key (or reads from env)
            headless: Whether to run browser headless
        """
        self.browser_manager = BrowserManager()
        self.vision_client = VisionClient(api_key=api_key)
        self.parser = ResponseParser()
        self.headless = headless
    
    async def discover(
        self,
        target_url: str,
        goal: str,
        initial_instruction: Optional[str] = None,
    ) -> CapabilityArtifact:
        """
        Discover automation flow for given goal.
        
        Args:
            target_url: URL of app to automate (e.g., "http://127.0.0.1:5000")
            goal: Natural language goal (e.g., "Look up member M001 and read savings balance")
            initial_instruction: Optional detailed instruction for Claude
        
        Returns:
            CapabilityArtifact describing the discovered automation
        
        Raises:
            Exception if discovery fails
        """
        try:
            logger.info("=" * 70)
            logger.info("STARTING DISCOVERY AGENT")
            logger.info("=" * 70)
            logger.info(f"Goal: {goal}")
            logger.info(f"Target: {target_url}")
            
            # Step 1: Connect browser
            await self.browser_manager.connect(target_url, headless=self.headless)
            current_url = await self.browser_manager.get_current_url()
            logger.info(f"Current URL: {current_url}")
            
            # Step 2: Take screenshot
            logger.info("\n[Step 1/4] Taking initial screenshot...")
            screenshot_b64 = await self.browser_manager.take_screenshot(
                filename="logs/discovery_initial.png"
            )
            
            # Step 3: Prepare prompt for Claude
            prompt = self._prepare_discovery_prompt(goal, initial_instruction)
            
            # Step 4: Send to Claude
            logger.info("\n[Step 2/4] Sending to Claude for analysis...")
            claude_response_text = self.vision_client.add_screenshot_to_context(
                screenshot_b64,
                prompt
            )
            logger.info("Claude response received")
            
            # Step 5: Parse JSON from response
            logger.info("\n[Step 3/4] Parsing Claude's response...")
            try:
                claude_json = self.vision_client.extract_json_from_response(
                    claude_response_text
                )
                logger.info("✅ Successfully extracted JSON from Claude response")
            except Exception as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"Raw response:\n{claude_response_text}")
                raise
            
            # Step 6: Convert to CapabilityArtifact
            logger.info("\n[Step 4/4] Converting to CapabilityArtifact...")
            artifact = self.parser.parse_discovery_response(
                claude_json,
                goal=goal
            )

            await self._verify_and_repair_artifact(artifact, goal)
            
            # Step 7: Save artifact
            artifact_path = self.parser.save_artifact(artifact)
            
            logger.info("\n" + "=" * 70)
            logger.info("✅ DISCOVERY COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Artifact ID: {artifact.id}")
            logger.info(f"Artifact saved to: {artifact_path}")
            logger.info(f"Steps discovered: {len(artifact.steps)}")
            logger.info(f"Parameters: {list(artifact.parameters.keys())}")
            logger.info(f"Outputs: {list(artifact.outputs.keys())}")
            
            return artifact
        
        except Exception as e:
            logger.error(f"\n❌ DISCOVERY FAILED: {e}")
            raise
        
        finally:
            # Always disconnect browser
            await self.browser_manager.disconnect()

    async def _verify_and_repair_artifact(self, artifact: CapabilityArtifact, goal: str) -> None:
        """Execute discovered non-sensitive steps and repair failed selectors once."""
        context = self._infer_discovery_parameters(artifact, goal)
        resolver = ParameterResolver()
        executor = StepExecutor(self.browser_manager)

        for index, step in enumerate(artifact.steps):
            if step.requires_human_approval:
                logger.info("Stopping discovery verification at human approval step '%s'", step.id)
                return

            try:
                value = resolver.resolve(step.value, context) if step.value is not None else None
                extracted = await executor.execute(step, value)
                if step.store_as:
                    context[step.store_as] = extracted or ""
                logger.info("Discovery verified step %s", step.id)
            except Exception as first_error:
                logger.warning("Discovery step %s failed; asking Claude for a repair", step.id)
                screenshot = await self.browser_manager.take_screenshot()
                repair_prompt = self._prepare_repair_prompt(goal, step, first_error)
                response = self.vision_client.add_screenshot_to_context(screenshot, repair_prompt)
                repair_json = self.vision_client.extract_json_from_response(response)
                repaired_steps = self.parser._parse_steps([repair_json.get("step", repair_json)])
                if not repaired_steps:
                    raise RuntimeError(f"Claude did not provide a repair for {step.id}") from first_error

                repaired_step = repaired_steps[0]
                repaired_step.id = step.id
                artifact.steps[index] = repaired_step
                value = resolver.resolve(repaired_step.value, context) if repaired_step.value else None
                extracted = await executor.execute(repaired_step, value)
                if repaired_step.store_as:
                    context[repaired_step.store_as] = extracted or ""
                logger.info("Claude repair verified step %s", repaired_step.id)

    @staticmethod
    def _infer_discovery_parameters(artifact: CapabilityArtifact, goal: str) -> dict:
        """Supply example values from the goal only for live discovery verification."""
        context = {}
        member_ids = re.findall(r"\b[A-Z]\d{3,}\b", goal)
        if member_ids and "member_id" in artifact.parameters:
            context["member_id"] = member_ids[0]
        for name, definition in artifact.parameters.items():
            if name not in context and definition.default is not None:
                context[name] = definition.default
        return context

    @staticmethod
    def _prepare_repair_prompt(goal: str, step: object, error: Exception) -> str:
        """Ask Claude for one corrected action after an observed UI failure."""
        return f"""The goal is: {goal}

The discovered step failed against the live UI:
- action: {step.action}
- selector: {step.target.selector}
- error: {error}

Use the current screenshot to identify the correct target. Return only JSON for one replacement step:
{{
  "action": "click|type|read|wait|submit|navigate|screenshot",
  "selector": "stable CSS, XPath, or Playwright text selector",
  "target_type": "css",
  "element_description": "why this target is correct",
  "value": "preserve the original value if needed",
  "store_as": "preserve the original store name if needed",
  "timeout_ms": 5000,
  "description": "what this replacement does"
}}"""
    
    def _prepare_discovery_prompt(
        self,
        goal: str,
        initial_instruction: Optional[str] = None,
    ) -> str:
        """
        Prepare prompt for Claude.
        
        Args:
            goal: User's goal
            initial_instruction: Optional detailed instruction
        
        Returns:
            Prompt text
        """
        instruction = initial_instruction or ""
        
        prompt = f"""You are an expert automation engineer. You will help me discover how to automate a legacy banking application.

GOAL: {goal}

{f"DETAILED INSTRUCTION: {instruction}" if instruction else ""}

TASK: Based on the screenshot, analyze the current page and generate a structured automation plan.

Please respond with a JSON object containing:
1. **goal**: String describing the automation goal
2. **parameters**: Dict of input parameters needed (name -> {{"type": "string", "description": "...", "required": true}})
3. **steps**: List of automation steps, each with:
   - action: "click", "type", "wait", "read", "submit", "navigate", or "screenshot"
   - selector: CSS selector for the element (e.g., "#button_id" or ".class-name")
   - target_type: "css" or "xpath" (default: "css")
   - element_description: Why this selector is reliable
   - value: For "type" action, the text to type (can use ${{param_name}} for substitution)
   - store_as: For "read" action, variable name to store extracted text
    - requires_human_approval: true for sensitive or irreversible actions that require an operator before execution
    - human_prompt: concise instruction for the operator when approval is required
   - timeout_ms: Timeout in milliseconds (default: 5000)
   - description: Human-readable description of this step
4. **outputs**: Dict of extracted data (name -> {{"type": "string", "description": "..."}})
5. **success_condition**: String describing successful completion
6. **tags**: List of tags for categorization

Example response format:
{{
    "goal": "Look up member M001 and extract savings balance",
    "parameters": {{
        "member_id": {{"type": "string", "description": "Member ID to search for", "required": true}}
    }},
    "steps": [
        {{
            "action": "click",
            "selector": "#member_search_btn",
            "target_type": "css",
            "element_description": "Search button with stable ID",
            "description": "Click the search button"
        }},
        {{
            "action": "type",
            "selector": "#member_id_input",
            "value": "${{member_id}}",
            "description": "Type member ID into search field"
        }},
        {{
            "action": "wait",
            "selector": ".member-detail",
            "timeout_ms": 5000,
            "description": "Wait for member detail page to load"
        }},
        {{
            "action": "read",
            "selector": ".savings-balance",
            "store_as": "balance",
            "description": "Extract the savings balance value"
        }}
    ],
    "outputs": {{
        "balance": {{"type": "string", "description": "Member's savings balance"}}
    }},
    "success_condition": "balance value is extracted and non-empty",
    "tags": ["member_lookup", "balance_inquiry"]
}}

Now analyze the screenshot and provide the JSON response."""

        return prompt


async def main():
    """Example usage of discovery agent."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize agent
    agent = DiscoveryAgent(headless=False)
    
    # Run discovery
    try:
        artifact = await agent.discover(
            target_url="http://127.0.0.1:5000",
            goal="Look up member M001 and read their savings balance",
            initial_instruction="""
            The app is a banking system. Start from the home page.
            You should see a 'Search Members' button or link.
            Search for member ID 'M001'.
            View the member details page.
            Read the savings balance from the page.
            """
        )
        
        print("\n✅ Discovery successful!")
        print(f"Artifact: {artifact.id}")
        print(f"Saved to: artifacts/{artifact.id}_v10.json")
    
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
