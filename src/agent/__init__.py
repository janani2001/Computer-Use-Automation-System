"""
Agent package - LLM-based discovery of automation flows.

Modules:
- browser.py: Playwright browser control
- vision.py: Claude API integration
- parser.py: Response parsing to CapabilityArtifact
- agent.py: Main discovery orchestration
"""

from src.agent.agent import DiscoveryAgent

__all__ = ["DiscoveryAgent"]
