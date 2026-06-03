"""Call Claude with structured JSON output and retry on schema failure."""

import json
import logging
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from guardrails.output_validation import extract_json_from_text, validate_agent_output
from provider import get_client, get_model

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_RETRIES = 3


def load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def call_structured_agent(
    system_prompt: str,
    user_content: str,
    schema: Type[T],
    *,
    max_retries: int = MAX_RETRIES,
) -> tuple[T | None, dict[str, Any]]:
    """Parse model output into schema; retry up to max_retries on validation errors."""
    client = get_client()
    model = get_model()
    schema_json = json.dumps(schema.model_json_schema(), indent=2)

    metadata: dict[str, Any] = {
        "attempts": 0,
        "validation_passes": 0,
        "validation_failures": [],
        "success": False,
    }

    last_raw = ""
    for attempt in range(1, max_retries + 1):
        metadata["attempts"] = attempt
        instruction = (
            f"{user_content}\n\n"
            "Respond with ONLY valid JSON matching this schema (no markdown):\n"
            f"{schema_json}"
        )
        if attempt > 1:
            instruction += (
                f"\n\nPrevious attempt failed validation: "
                f"{metadata['validation_failures'][-1]}. Fix and return valid JSON."
            )

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": instruction}],
        )
        last_raw = response.content[0].text

        try:
            data = extract_json_from_text(last_raw)
        except json.JSONDecodeError as e:
            err = f"JSON parse error: {e}"
            metadata["validation_failures"].append(err)
            logger.warning("Attempt %s: %s", attempt, err)
            continue

        ok, parsed, errs = validate_agent_output(data, schema)
        if ok and parsed is not None:
            metadata["validation_passes"] = 1
            metadata["success"] = True
            return parsed, metadata

        metadata["validation_failures"].append(errs)
        logger.warning("Attempt %s schema validation failed: %s", attempt, errs)

    metadata["last_raw"] = last_raw
    return None, metadata
