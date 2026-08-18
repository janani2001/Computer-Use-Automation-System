"""
Parser module - Converts Claude responses to CapabilityArtifact schema.

Responsible for:
- Converting Claude's described steps to AutomationStep objects
- Extracting parameters and outputs
- Validating against schema
- Saving artifacts to JSON
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.artifacts.schema import (
    CapabilityArtifact,
    AutomationStep,
    ElementTarget,
    ParameterDefinition,
    OutputField,
    ErrorHandler,
)

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse Claude responses and convert to CapabilityArtifact."""
    
    def __init__(self):
        """Initialize parser."""
        self.artifacts_dir = Path("artifacts")
        self.artifacts_dir.mkdir(exist_ok=True)
    
    def parse_discovery_response(
        self,
        claude_response: Dict[str, Any],
        goal: str,
    ) -> CapabilityArtifact:
        """
        Convert Claude's structured response to CapabilityArtifact.
        
        Expects Claude response format like:
        {
            "goal": "...",
            "parameters": {
                "param_name": {"type": "string", "description": "..."}
            },
            "steps": [
                {
                    "action": "click",
                    "selector": "#button_id",
                    "description": "..."
                },
                ...
            ],
            "outputs": {
                "output_name": {"type": "string", "description": "..."}
            }
        }
        
        Args:
            claude_response: Parsed JSON from Claude
            goal: Original goal string
        
        Returns:
            CapabilityArtifact instance
        
        Raises:
            ValueError if response format is invalid
        """
        try:
            logger.info("Parsing Claude discovery response...")
            
            # Extract goal from response or use provided goal
            actual_goal = claude_response.get("goal", goal)
            
            # Extract artifact ID from goal (remove spaces, lowercase)
            artifact_id = (
                actual_goal.lower()
                .replace(" ", "_")[:50]
                .replace(" ", "_")
            )
            
            # Parse parameters
            parameters = self._parse_parameters(claude_response.get("parameters", {}))
            logger.info(f"Parsed {len(parameters)} parameters")
            
            # Parse steps
            steps = self._parse_steps(claude_response.get("steps", []))
            logger.info(f"Parsed {len(steps)} automation steps")
            
            # Parse outputs
            outputs = self._parse_outputs(claude_response.get("outputs", {}))
            logger.info(f"Parsed {len(outputs)} output fields")
            
            # Create artifact
            artifact = CapabilityArtifact(
                version="1.0",
                id=artifact_id,
                name=actual_goal,
                goal=actual_goal,
                parameters=parameters,
                steps=steps,
                outputs=outputs,
                success_condition=claude_response.get(
                    "success_condition",
                    "All steps completed successfully"
                ),
                tags=claude_response.get("tags", []),
            )
            
            logger.info(f"✅ Created artifact: {artifact.id}")
            return artifact
        
        except Exception as e:
            logger.error(f"❌ Failed to parse discovery response: {e}")
            raise
    
    def _parse_parameters(
        self,
        params_dict: Dict[str, Any]
    ) -> Dict[str, ParameterDefinition]:
        """
        Parse parameters from Claude response.
        
        Args:
            params_dict: Dictionary of parameters from Claude
        
        Returns:
            Dictionary of ParameterDefinition objects
        """
        parameters = {}
        
        for param_name, param_info in params_dict.items():
            try:
                param_def = ParameterDefinition(
                    type=param_info.get("type", "string"),
                    description=param_info.get("description", ""),
                    required=param_info.get("required", True),
                    default=param_info.get("default"),
                )
                parameters[param_name] = param_def
                logger.debug(f"Parsed parameter: {param_name}")
            
            except Exception as e:
                logger.warning(f"Failed to parse parameter {param_name}: {e}")
        
        return parameters
    
    def _parse_steps(self, steps_list: List[Dict[str, Any]]) -> List[AutomationStep]:
        """
        Parse automation steps from Claude response.
        
        Args:
            steps_list: List of step dictionaries from Claude
        
        Returns:
            List of AutomationStep objects
        """
        steps = []
        
        for idx, step_info in enumerate(steps_list):
            try:
                # Create element target
                target = ElementTarget(
                    selector=step_info.get("selector"),
                    type=step_info.get("target_type", "css"),
                    coordinates=step_info.get("coordinates"),
                    accessibility_label=step_info.get("accessibility_label"),
                    description=step_info.get("element_description", ""),
                )
                
                # Create step
                step = AutomationStep(
                    id=f"step_{idx + 1}",
                    action=step_info.get("action", "click"),
                    target=target,
                    value=step_info.get("value"),
                    store_as=step_info.get("store_as"),
                    requires_human_approval=step_info.get("requires_human_approval", False),
                    human_prompt=step_info.get("human_prompt"),
                    timeout_ms=step_info.get("timeout_ms", 5000),
                    description=step_info.get("description", ""),
                )
                
                steps.append(step)
                logger.debug(f"Parsed step {idx + 1}: {step.action} on {step.target.selector}")
            
            except Exception as e:
                logger.warning(f"Failed to parse step {idx + 1}: {e}")
        
        return steps
    
    def _parse_outputs(
        self,
        outputs_dict: Dict[str, Any]
    ) -> Dict[str, OutputField]:
        """
        Parse output fields from Claude response.
        
        Args:
            outputs_dict: Dictionary of outputs from Claude
        
        Returns:
            Dictionary of OutputField objects
        """
        outputs = {}
        
        for output_name, output_info in outputs_dict.items():
            try:
                output_field = OutputField(
                    type=output_info.get("type", "string"),
                    description=output_info.get("description", ""),
                )
                outputs[output_name] = output_field
                logger.debug(f"Parsed output: {output_name}")
            
            except Exception as e:
                logger.warning(f"Failed to parse output {output_name}: {e}")
        
        return outputs
    
    def save_artifact(self, artifact: CapabilityArtifact) -> Path:
        """
        Save artifact to JSON file.
        
        Args:
            artifact: CapabilityArtifact to save
        
        Returns:
            Path to saved file
        """
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{artifact.id}_v{artifact.version.replace('.', '')}.json"
            filepath = self.artifacts_dir / filename
            
            # Save to file
            json_str = artifact.model_dump_json(indent=2)
            filepath.write_text(json_str)
            
            logger.info(f"✅ Artifact saved to {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"❌ Failed to save artifact: {e}")
            raise
    
    def load_artifact(self, filepath: Path) -> CapabilityArtifact:
        """
        Load and validate artifact from JSON file.
        
        Args:
            filepath: Path to JSON artifact file
        
        Returns:
            CapabilityArtifact instance
        
        Raises:
            ValueError if file invalid or artifact validation fails
        """
        try:
            json_str = filepath.read_text()
            artifact = CapabilityArtifact.model_validate_json(json_str)
            logger.info(f"✅ Loaded artifact from {filepath}")
            return artifact
        
        except Exception as e:
            logger.error(f"❌ Failed to load artifact from {filepath}: {e}")
            raise
