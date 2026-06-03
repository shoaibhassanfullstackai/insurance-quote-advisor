"""Anthropic client and default model."""

import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


def get_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Anthropic(api_key=api_key)


def get_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
