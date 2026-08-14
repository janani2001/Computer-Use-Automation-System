#!/usr/bin/env python3
"""
Entry point for the agent discovery loop.

Usage:
    python main.py --goal "Look up member 12345 and read their savings balance" --target "http://localhost:8000"
"""

import argparse
import logging

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
        "--output",
        default="artifacts/",
        help="Directory to save artifacts (default: artifacts/)",
    )

    args = parser.parse_args()

    print(f"Goal: {args.goal}")
    print(f"Target: {args.target}")
    print(f"Output: {args.output}")
    print("\n[TODO] Implement agent discovery loop")
