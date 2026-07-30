from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def llm_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def explain_plan_with_llm(request: dict[str, Any], plans: list[dict[str, Any]]) -> str | None:
    """Optional language layer. Planning math remains deterministic Python."""
    if not llm_is_configured():
        return None

    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5"),
        instructions=(
            "You are PlanPilot, a practical outing-planning assistant. Explain the ranked plans clearly. "
            "Never invent availability, opening hours, prices, or travel times. State that this V1 uses sample venue data."
        ),
        input=f"Request:\n{json.dumps(request)}\n\nRanked plans:\n{json.dumps(plans)}",
    )
    return response.output_text
