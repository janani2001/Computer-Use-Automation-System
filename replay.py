#!/usr/bin/env python3
"""
Entry point for deterministic replay of saved artifacts.

Usage:
    python replay.py --artifact artifacts/lookup_member_v1.json \
        --target "http://127.0.0.1:5000" --params '{"member_id": "M001"}'
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path

from src.agent.browser import BrowserManager
from src.agent.parser import ResponseParser
from src.replay.engine import ReplayEngine

logging.basicConfig(level=logging.INFO)


async def _run(
    artifact_path: Path,
    target_url: str,
    params: dict,
    headless: bool,
    interactive: bool,
) -> None:
    artifact = ResponseParser().load_artifact(artifact_path)

    engine = ReplayEngine(BrowserManager())
    result = await engine.run(
        artifact,
        target_url=target_url,
        params=params,
        headless=headless,
        interactive=interactive,
    )

    print(json.dumps(result.model_dump(), indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Replay a saved automation artifact"
    )
    parser.add_argument(
        "--artifact",
        required=True,
        help="Path to the artifact JSON file",
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target application URL (e.g. http://127.0.0.1:5000)",
    )
    parser.add_argument(
        "--params",
        type=json.loads,
        default="{}",
        help="Input parameters as JSON (e.g., '{\"member_id\": \"M001\"}')",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser without a visible window",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Pause for a human to fix the browser state, then retry the failed step",
    )

    args = parser.parse_args()

    if args.interactive and args.headless:
        parser.error("--interactive requires a visible browser; remove --headless")

    asyncio.run(
        _run(Path(args.artifact), args.target, args.params, args.headless, args.interactive)
    )

