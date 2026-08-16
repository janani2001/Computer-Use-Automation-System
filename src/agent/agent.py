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
from typing import Optional
from pathlib import Path

from src.agent.browser import BrowserManager
from src.agent.vision import VisionClient
from src.agent.parser import ResponseParser
from src.artifacts.schema import CapabilityArtifact

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
