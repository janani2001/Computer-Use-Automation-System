"""
This file shows examples of creating, validating and serializing artifacts.
"""

from src.artifacts.schema import (
    CapabilityArtifact,
    AutomationStep,
    ElementTarget,
    ParameterDefinition,
    OutputField,
)
import json


# ============================================================================
# EXAMPLE 1: Create an artifact programmatically
# ============================================================================

def create_example_artifact():
    """Create a 'look up member balance' capability."""
    
    artifact = CapabilityArtifact(
        # Metadata
        version="1.0",
        id="lookup_member_balance",
        name="Look up Member Balance",
        goal="Look up a member by ID and extract their savings balance",
        
        # Inputs
        parameters={
            "member_id": ParameterDefinition(
                type="string",
                description="The member ID to look up",
                required=True
            )
        },
        
        # Steps
        steps=[
            AutomationStep(
                id="step_1",
                action="click",
                target=ElementTarget(
                    selector="#member_search_btn",
                    type="css",
                    description="Search button has a stable ID"
                ),
                description="Click the member search button"
            ),
            
            AutomationStep(
                id="step_2",
                action="type",
                target=ElementTarget(
                    selector="#member_id_input",
                    type="css",
                    description="Input field for member ID"
                ),
                value="${member_id}",
                description="Type the member ID into the search field"
            ),
            
            AutomationStep(
                id="step_3",
                action="submit",
                target=ElementTarget(
                    selector="button[type='submit']",
                    type="css",
                    description="Submit button"
                ),
                timeout_ms=3000,
                description="Submit the search form"
            ),
            
            AutomationStep(
                id="step_4",
                action="wait",
                target=ElementTarget(
                    selector=".member-detail",
                    type="css",
                    description="Wait for member detail section to appear"
                ),
                timeout_ms=5000,
                description="Wait for results to load"
            ),
            
            AutomationStep(
                id="step_5",
                action="read",
                target=ElementTarget(
                    selector=".savings-balance",
                    type="css",
                    description="Savings balance display"
                ),
                store_as="balance",
                description="Extract the savings balance value"
            ),
        ],
        
        # Outputs
        outputs={
            "balance": OutputField(
                type="string",
                description="Member's current savings balance"
            )
        },
        
        # Success
        success_condition="balance value is extracted and non-empty",
        
        # Tags
        tags=["member_lookup", "balance_inquiry", "banking"]
    )
    
    return artifact


# ============================================================================
# EXAMPLE 2: Save to JSON
# ============================================================================

def save_example():
    """Save artifact to JSON file."""
    artifact = create_example_artifact()
    
    # Convert to JSON
    json_str = artifact.model_dump_json(indent=2)
    
    # Save to file
    with open("artifacts/example_artifact.json", "w") as f:
        f.write(json_str)
    
    print("✅ Saved to artifacts/example_artifact.json")
    print("\nPreview:")
    print(json_str[:500] + "...")


# ============================================================================
# EXAMPLE 3: Load from JSON and validate
# ============================================================================

def load_example():
    """Load and validate artifact from JSON."""
    with open("artifacts/example_artifact.json", "r") as f:
        json_str = f.read()
    
    # Pydantic validates automatically
    artifact = CapabilityArtifact.model_validate_json(json_str)
    
    print("✅ Loaded and validated artifact:")
    print(f"   ID: {artifact.id}")
    print(f"   Goal: {artifact.goal}")
    print(f"   Steps: {len(artifact.steps)}")
    print(f"   Outputs: {list(artifact.outputs.keys())}")
    
    return artifact


# ============================================================================
# EXAMPLE 4: Show why validation matters
# ============================================================================

def show_validation():
    """Demonstrate validation catching errors."""
    
    print("\n--- VALIDATION EXAMPLE ---\n")
    
    # This works ✅
    print("1. Creating VALID artifact...")
    try:
        valid = create_example_artifact()
        print("   ✅ Success! Artifact created and validated")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # This FAILS ❌
    print("\n2. Creating INVALID artifact (wrong types)...")
    try:
        invalid = CapabilityArtifact(
            version=1,  # ❌ Should be string
            id="test",
            name="test",
            goal="test",
            steps=[],
            success_condition="test"
        )
    except Exception as e:
        print(f"   ❌ Caught error (as expected):")
        print(f"   {str(e)[:200]}...")
    
    # This also FAILS ❌
    print("\n3. Creating artifact with missing required field...")
    try:
        invalid = CapabilityArtifact(
            version="1.0",
            id="test",
            name="test",
            goal="test",
            # Missing 'steps' ❌
            success_condition="test"
        )
    except Exception as e:
        print(f"   ❌ Caught error (as expected):")
        print(f"   {str(e)[:200]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("ARTIFACT SCHEMA EXAMPLES")
    print("=" * 60)
    
    # Show validation
    show_validation()
    
    print("\n" + "=" * 60)
    print("Creating and displaying example artifact...")
    print("=" * 60)
    artifact = create_example_artifact()
    print(json.dumps(json.loads(artifact.model_dump_json()), indent=2)[:1000])
    print("\n... (truncated for brevity)")
