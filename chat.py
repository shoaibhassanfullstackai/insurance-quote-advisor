#!/usr/bin/env python3
"""CLI for the home insurance quote advisor."""

from __future__ import annotations

import argparse
import json

import bootstrap  # noqa: F401 — adds project root to sys.path

from workflow import QuoteWorkflow


def load_profile(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Profile not found: {path}")
    return json.loads(p.read_text(encoding="utf-8"))


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2))


def interactive_loop(workflow: QuoteWorkflow, profile: dict) -> None:
    print("Running quote pipeline...\n")
    result = workflow.handle_message(json.dumps(profile), profile_json=profile)
    print_json(result)

    if result.get("error") or result.get("type") != "quote":
        return

    print("\nAsk a follow-up about this quote (Enter to skip):\n")
    question = input("> ").strip()
    if not question:
        return

    print_json(workflow.handle_message(question))


def main() -> None:
    parser = argparse.ArgumentParser(description="Home insurance quote advisor")
    parser.add_argument("-p", "--profile", help="Path to customer profile JSON")
    parser.add_argument("--inline", help="Inline profile JSON string")
    parser.add_argument(
        "-f",
        "--follow-up",
        help="Follow-up question after generating a quote",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Prompt for a follow-up after the quote",
    )
    args = parser.parse_args()

    workflow = QuoteWorkflow()

    if args.profile:
        profile = load_profile(args.profile)
        result = workflow.handle_message(json.dumps(profile), profile_json=profile)
        print_json(result)

        if args.follow_up and result.get("type") == "quote":
            print_json(workflow.handle_message(args.follow_up))
        elif args.interactive and result.get("type") == "quote":
            question = input("\nFollow-up> ").strip()
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
        print("Paste profile JSON, then blank line:")
        lines = []
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
        interactive_loop(workflow, json.loads("\n".join(lines)))
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
