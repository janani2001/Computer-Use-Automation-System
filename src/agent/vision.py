"""
Vision module - Handles Claude API integration for UI understanding.

Uses Claude 3.5 Sonnet with vision capabilities to:
- Analyze screenshots
- Understand UI state
- Generate automation steps
- Extract structured responses
"""

import json
import logging
from typing import Optional, Dict, Any
import os

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class VisionClient:
    """Client for Claude 3.5 Sonnet with vision capabilities."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize vision client.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.conversation_history = []
        
        logger.info(f"✅ Vision client initialized (model={self.model})")
    
    def add_screenshot_to_context(
        self,
        screenshot_b64: str,
        message: str
    ) -> str:
        """
        Send screenshot and message to Claude, get response.
        
        Args:
            screenshot_b64: Base64-encoded screenshot
            message: Text message/prompt for Claude
        
        Returns:
            Claude's response text
        """
        try:
            logger.info(f"Sending screenshot to Claude ({len(screenshot_b64)} bytes)...")
            logger.debug(f"Message: {message}")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": message,
                    }
                ],
            })
            
            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=self.conversation_history,
            )
            
            # Extract response text
            response_text = response.content[0].text
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
            })
            
            logger.info(f"✅ Claude responded ({len(response_text)} chars)")
            logger.debug(f"Response: {response_text[:500]}...")
            
            return response_text
        
        except Exception as e:
            logger.error(f"❌ Vision API error: {e}")
            raise
    
    def send_text_message(self, message: str) -> str:
        """
        Send text-only message to Claude (no screenshot).
        
        Args:
            message: Text message
        
        Returns:
            Claude's response
        """
        try:
            logger.info("Sending text message to Claude...")
            logger.debug(f"Message: {message}")
            
            # Add to history
            self.conversation_history.append({
                "role": "user",
                "content": message,
            })
            
            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=self.conversation_history,
            )
            
            # Extract response
            response_text = response.content[0].text
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
            })
            
            logger.info(f"✅ Claude responded ({len(response_text)} chars)")
            return response_text
        
        except Exception as e:
            logger.error(f"❌ Text message API error: {e}")
            raise
    
    def extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON object from Claude response.
        
        Handles cases where Claude wraps JSON in markdown code blocks.
        
        Args:
            response: Claude's response text
        
        Returns:
            Parsed JSON dictionary
        
        Raises:
            ValueError if no JSON found or invalid JSON
        """
        try:
            # Try direct JSON parsing first
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            
            # Try extracting from markdown code block
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            # Try extracting from plain code block
            if "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end > start:
                    json_str = response[start:end].strip()
                    return json.loads(json_str)
            
            # If all else fails, raise error
            logger.error("Could not extract JSON from response")
            logger.error(f"Response: {response[:500]}")
            raise ValueError("No valid JSON found in Claude response")
        
        except Exception as e:
            logger.error(f"❌ JSON extraction failed: {e}")
            raise
    
    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh start."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
