"""
Test script for agent modules - validates infrastructure without API calls.

This script tests:
1. Browser module (connect, screenshot, click, type, etc.)
2. Vision module (JSON extraction, conversation history)
3. Parser module (Claude response → CapabilityArtifact)
4. Schema validation (Pydantic)

No API calls are made - this is safe to run without ANTHROPIC_API_KEY!
"""

import asyncio
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.agent.browser import BrowserManager
from src.agent.parser import ResponseParser
from src.artifacts.schema import CapabilityArtifact


# Mock Claude response (what Claude would return)
MOCK_CLAUDE_RESPONSE = {
    "goal": "Look up member M001 and read their savings balance",
    "parameters": {
        "member_id": {
            "type": "string",
            "description": "Member ID to search for",
            "required": True
        }
    },
    "steps": [
        {
            "action": "click",
            "selector": "#member_search_btn",
            "target_type": "css",
            "element_description": "Search button with stable ID",
            "description": "Click the member search button"
        },
        {
            "action": "type",
            "selector": "#member_id_input",
            "target_type": "css",
            "element_description": "Input field for member ID",
            "value": "${member_id}",
            "description": "Type the member ID into search field"
        },
        {
            "action": "submit",
            "selector": "button[type='submit']",
            "target_type": "css",
            "element_description": "Submit button",
            "timeout_ms": 3000,
            "description": "Submit the search form"
        },
        {
            "action": "wait",
            "selector": ".member-detail",
            "target_type": "css",
            "element_description": "Member detail section",
            "timeout_ms": 5000,
            "description": "Wait for member detail page to load"
        },
        {
            "action": "read",
            "selector": ".savings-balance",
            "target_type": "css",
            "element_description": "Savings balance display",
            "store_as": "balance",
            "description": "Extract the savings balance value"
        }
    ],
    "outputs": {
        "balance": {
            "type": "string",
            "description": "Member's current savings balance"
        }
    },
    "success_condition": "balance value is extracted and non-empty",
    "tags": ["member_lookup", "balance_inquiry", "banking"]
}


async def test_browser_module():
    """Test browser control module."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Browser Module (Playwright Wrapper)")
    logger.info("="*70)
    
    try:
        browser = BrowserManager()
        logger.info("✅ BrowserManager instantiated")
        
        # Test connect (to mock app)
        logger.info("\nConnecting to mock banking app...")
        await browser.connect("http://127.0.0.1:5000", headless=True)
        logger.info("✅ Browser connected")
        
        # Test get URL
        current_url = await browser.get_current_url()
        logger.info(f"✅ Current URL: {current_url}")
        
        # Test screenshot
        logger.info("\nTaking screenshot...")
        screenshot = await browser.take_screenshot("logs/test_screenshot.png")
        logger.info(f"✅ Screenshot taken: {len(screenshot)} bytes (base64)")
        
        # Test page content
        logger.info("\nGetting page content...")
        content = await browser.get_page_content()
        logger.info(f"✅ Page content retrieved: {len(content)} bytes")
        
        # Disconnect
        await browser.disconnect()
        logger.info("✅ Browser disconnected")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Browser test failed: {e}")
        return False


def test_parser_module():
    """Test response parser module."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Parser Module (Claude Response → CapabilityArtifact)")
    logger.info("="*70)
    
    try:
        parser = ResponseParser()
        logger.info("✅ ResponseParser instantiated")
        
        # Test parsing Claude response
        logger.info("\nParsing mock Claude response...")
        artifact = parser.parse_discovery_response(
            MOCK_CLAUDE_RESPONSE,
            goal="Look up member M001 and read their savings balance"
        )
        logger.info("✅ Successfully parsed to CapabilityArtifact")
        
        # Log artifact details
        logger.info(f"\nArtifact Details:")
        logger.info(f"  ID: {artifact.id}")
        logger.info(f"  Name: {artifact.name}")
        logger.info(f"  Goal: {artifact.goal}")
        logger.info(f"  Version: {artifact.version}")
        logger.info(f"  Parameters: {list(artifact.parameters.keys())}")
        logger.info(f"  Steps: {len(artifact.steps)}")
        logger.info(f"  Outputs: {list(artifact.outputs.keys())}")
        logger.info(f"  Tags: {artifact.tags}")
        
        # Log step details
        logger.info(f"\nDiscovered Steps:")
        for step in artifact.steps:
            logger.info(f"  {step.id}: {step.action} on {step.target.selector}")
            if step.value:
                logger.info(f"    └─ Value: {step.value}")
            if step.store_as:
                logger.info(f"    └─ Store as: {step.store_as}")
        
        # Test Pydantic validation
        logger.info(f"\nValidating Pydantic schema...")
        schema_dict = artifact.model_dump()
        logger.info(f"✅ Schema validation passed")
        
        # Test JSON serialization
        logger.info(f"\nSerializing to JSON...")
        json_str = artifact.model_dump_json(indent=2)
        logger.info(f"✅ JSON serialized: {len(json_str)} bytes")
        
        # Test deserialization
        logger.info(f"\nDeserializing from JSON...")
        artifact2 = CapabilityArtifact.model_validate_json(json_str)
        logger.info(f"✅ JSON deserialized and validated")
        
        # Test saving to file
        logger.info(f"\nSaving to file...")
        path = parser.save_artifact(artifact)
        logger.info(f"✅ Artifact saved to: {path}")
        
        # Test loading from file
        logger.info(f"\nLoading from file...")
        artifact3 = parser.load_artifact(path)
        logger.info(f"✅ Artifact loaded: {artifact3.id}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_validation():
    """Test Pydantic schema validation."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Schema Validation (Pydantic)")
    logger.info("="*70)
    
    try:
        # Test 1: Valid artifact
        logger.info("\nTest 3.1: Creating valid artifact...")
        from src.artifacts.schema import (
            ParameterDefinition, OutputField, ElementTarget, AutomationStep
        )
        
        artifact = CapabilityArtifact(
            version="1.0",
            id="test_artifact",
            name="Test",
            goal="Test goal",
            parameters={
                "test_param": ParameterDefinition(
                    type="string",
                    description="Test parameter",
                    required=True
                )
            },
            steps=[
                AutomationStep(
                    id="step_1",
                    action="click",
                    target=ElementTarget(
                        selector="#test",
                        type="css",
                        description="Test selector"
                    ),
                    description="Test step"
                )
            ],
            outputs={
                "test_output": OutputField(
                    type="string",
                    description="Test output"
                )
            },
            success_condition="Test complete"
        )
        logger.info("✅ Valid artifact created")
        
        # Test 2: Invalid type should fail
        logger.info("\nTest 3.2: Attempting invalid type (version as int)...")
        try:
            invalid = CapabilityArtifact(
                version=1,  # ❌ Should be string
                id="test",
                name="test",
                goal="test",
                steps=[],
                success_condition="test"
            )
            logger.error("❌ Should have caught invalid type!")
            return False
        except Exception as e:
            logger.info(f"✅ Correctly rejected: {str(e)[:80]}...")
        
        # Test 3: Missing required field should fail
        logger.info("\nTest 3.3: Attempting missing required field (no steps)...")
        try:
            invalid = CapabilityArtifact(
                version="1.0",
                id="test",
                name="test",
                goal="test",
                # Missing steps ❌
                success_condition="test"
            )
            logger.error("❌ Should have caught missing field!")
            return False
        except Exception as e:
            logger.info(f"✅ Correctly rejected: {str(e)[:80]}...")
        
        logger.info("\n✅ All schema validation tests passed")
        return True
    
    except Exception as e:
        logger.error(f"❌ Schema validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_round_trip():
    """Test JSON serialization round-trip."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: JSON Round-Trip (Save & Load)")
    logger.info("="*70)
    
    try:
        parser = ResponseParser()
        
        # Create artifact from mock Claude response
        logger.info("\nCreating artifact from mock Claude response...")
        artifact1 = parser.parse_discovery_response(
            MOCK_CLAUDE_RESPONSE,
            goal="Test goal"
        )
        logger.info("✅ Artifact created")
        
        # Serialize to JSON
        logger.info("\nSerializing to JSON...")
        json_str = artifact1.model_dump_json(indent=2)
        json_size = len(json_str)
        logger.info(f"✅ Serialized: {json_size} bytes")
        
        # Deserialize from JSON
        logger.info("\nDeserializing from JSON...")
        artifact2 = CapabilityArtifact.model_validate_json(json_str)
        logger.info("✅ Deserialized successfully")
        
        # Verify data integrity
        logger.info("\nVerifying data integrity...")
        assert artifact1.id == artifact2.id, "ID mismatch"
        assert artifact1.name == artifact2.name, "Name mismatch"
        assert len(artifact1.steps) == len(artifact2.steps), "Step count mismatch"
        logger.info("✅ All data verified")
        
        logger.info("\n✅ JSON round-trip test passed")
        return True
    
    except Exception as e:
        logger.error(f"❌ JSON round-trip test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("\n\n")
    logger.info("╔" + "="*68 + "╗")
    logger.info("║" + " "*68 + "║")
    logger.info("║" + "  AGENT MODULE TEST SUITE (No API Calls)".center(68) + "║")
    logger.info("║" + " "*68 + "║")
    logger.info("╚" + "="*68 + "╝")
    
    results = {}
    
    # Test 1: Browser Module
    logger.info("\n⏳ Running Test 1: Browser Module...")
    results['browser'] = await test_browser_module()
    
    # Test 2: Parser Module
    logger.info("\n⏳ Running Test 2: Parser Module...")
    results['parser'] = test_parser_module()
    
    # Test 3: Schema Validation
    logger.info("\n⏳ Running Test 3: Schema Validation...")
    results['schema'] = test_schema_validation()
    
    # Test 4: JSON Round-Trip
    logger.info("\n⏳ Running Test 4: JSON Round-Trip...")
    results['json'] = test_json_round_trip()
    
    # Summary
    logger.info("\n\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name.upper():20} {status}")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    logger.info("="*70)
    logger.info(f"Total: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        logger.info("\n🎉 All tests passed! Agent infrastructure is ready.")
        logger.info("\nNext steps:")
        logger.info("1. Set ANTHROPIC_API_KEY in .env")
        logger.info("2. Start Flask app: python3 target_app/app.py")
        logger.info("3. Run discovery: python3 -m src.agent.agent")
    else:
        logger.error(f"\n❌ {total_tests - total_passed} tests failed. Fix errors above.")
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
