#!/usr/bin/env python3
"""
CLI entry point for the Multi-Agent Home Insurance Quote Advisor.

Usage:
  python chat.py --profile data/profile_a.json
  python chat.py --profile data/profile_b.json --follow-up "Why is this quote expensive?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow import QuoteWorkflow 


def load_profile(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Profile not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2))


def interactive_loop(workflow: QuoteWorkflow, profile: dict) -> None:
    print("Generating quote from profile...\n")
    result = workflow.handle_message(json.dumps(profile), profile_json=profile)
    print_json(result)

    if result.get("error") or result.get("type") != "quote":
        return

    print("\n--- Follow-up (session memory active) ---")
    print("Ask a question about this quote (e.g. 'Why is this quote expensive?')")
    print("Press Enter to skip.\n")
    question = input("Follow-up> ").strip()
    if not question:
        print("Skipped follow-up.")
        return

    follow = workflow.handle_message(question)
    print_json(follow)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Home Insurance Quote Advisor"
    )
    parser.add_argument(
        "--profile",
        "-p",
        help="Path to customer profile JSON file",
    )
    parser.add_argument(
        "--inline",
        help="Inline JSON customer profile string",
    )
    parser.add_argument(
        "--follow-up",
        "-f",
        help="Follow-up question (runs after quote; use with --profile)",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode: quote then prompt for follow-up",
    )
    args = parser.parse_args()

    workflow = QuoteWorkflow()

    if args.profile:
        profile = load_profile(args.profile)
        result = workflow.handle_message(json.dumps(profile), profile_json=profile)
        print_json(result)

        if args.follow_up and result.get("type") == "quote":
            print("\n--- Follow-up response ---\n")
            follow = workflow.handle_message(args.follow_up)
            print_json(follow)
        elif args.interactive and result.get("type") == "quote":
            print("\n--- Follow-up (session memory active) ---")
            question = input("Follow-up> ").strip()
            if question:
                print_json(workflow.handle_message(question))
        return

    if args.inline:
        profile = json.loads(args.inline)
        result = workflow.handle_message(json.dumps(profile), profile_json=profile)
        print_json(result)
        if args.follow_up and result.get("type") == "quote":
            print_json(workflow.handle_message(args.follow_up))
        return

    if args.interactive:
        print("Paste customer profile JSON, then press Enter twice:")
        lines = []
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
        profile = json.loads("\n".join(lines))
        interactive_loop(workflow, profile)
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
