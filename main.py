#!/usr/bin/env python3
"""
Entry point for the agent discovery loop.

Usage:
    python main.py --goal "Look up member 12345 and read their savings balance" --target "http://localhost:8000"
"""

import argparse
import asyncio
import logging

from dotenv import load_dotenv

from src.agent.agent import DiscoveryAgent

logging.basicConfig(level=logging.INFO)
load_dotenv()


async def _run(goal: str, target: str, headless: bool) -> None:
    agent = DiscoveryAgent(headless=headless)
    artifact = await agent.discover(target_url=target, goal=goal)

    print(f"\nArtifact ID: {artifact.id}")
    print(f"Steps discovered: {len(artifact.steps)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the computer-use agent to accomplish a goal"
    )
    parser.add_argument(
        "--goal",
        required=True,
        help="Natural language goal (e.g., 'Look up member 12345 and read balance')",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target application URL or entry point",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser without a visible window",
    )

    args = parser.parse_args()

    print(f"Goal: {args.goal}")
    print(f"Target: {args.target}")

    asyncio.run(_run(args.goal, args.target, args.headless))

