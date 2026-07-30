import json
import os
import re

from dotenv import load_dotenv

from backend.app.models import ParsedPlanRequest

load_dotenv()


def _fallback_parse(text: str) -> ParsedPlanRequest:
    lowered = text.lower()

    budget_match = re.search(
        r"(?:under|below|max(?:imum)?|budget(?: of)?|up to)\s*\$?(\d+(?:\.\d+)?)",
        lowered,
    )

    people_match = re.search(
        r"(?:for|party of)\s+(\d+)\s+(?:people|persons?|guests?)",
        lowered,
    )

    travel_match = re.search(
        r"(?:under|max(?:imum)?|within)\s+(\d+)\s+minutes?",
        lowered,
    )

    time_match = re.search(
        r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b",
        lowered,
    )

    city = "Boston"
    common_cities = [
        "Boston",
        "New York",
        "Chicago",
        "Miami",
        "Seattle",
        "San Francisco",
        "Providence",
        "Salem",
    ]

    for candidate in common_cities:
        if candidate.lower() in lowered:
            city = candidate
            break

    return ParsedPlanRequest(
        city=city,
        budget=float(budget_match.group(1)) if budget_match else 200,
        party_size=int(people_match.group(1)) if people_match else 2,
        max_travel_minutes=int(travel_match.group(1)) if travel_match else 30,
        vibe=_detect_vibe(lowered),
        include_activity=any(
            word in lowered
            for word in ["activity", "karaoke", "movie", "museum", "bowling", "game"]
        ),
        include_dinner=any(
            word in lowered
            for word in ["dinner", "restaurant", "food", "eat"]
        ),
        include_dessert=any(
            word in lowered
            for word in ["dessert", "ice cream", "bakery", "sweets"]
        ),
        transportation=(
            "public_transit"
            if any(
                phrase in lowered
                for phrase in [
                    "public transit",
                    "no car",
                    "train",
                    "subway",
                    "bus",
                ]
            )
            else "any"
        ),
        start_time=time_match.group(1).upper() if time_match else None,
        date_text=_detect_date(lowered),
    )


def _detect_vibe(text: str) -> str:
    vibe_words = {
        "romantic": ["romantic", "date", "cute"],
        "fun": ["fun", "lively", "exciting"],
        "chill": ["chill", "relaxed", "quiet"],
        "fancy": ["fancy", "upscale", "luxury"],
    }

    for vibe, words in vibe_words.items():
        if any(word in text for word in words):
            return vibe

    return "romantic"


def _detect_date(text: str) -> str | None:
    date_words = [
        "today",
        "tomorrow",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    for word in date_words:
        if word in text:
            return word.title()

    return None


def parse_natural_language_request(text: str) -> ParsedPlanRequest:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return _fallback_parse(text)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5")

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract outing-planning requirements from the user's text. "
                        "Return only valid JSON with these keys: city, budget, "
                        "party_size, max_travel_minutes, vibe, include_activity, "
                        "include_dinner, include_dessert, transportation, "
                        "start_time, date_text. Use sensible defaults when missing."
                    ),
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )

        raw_text = response.output_text.strip()
        data = json.loads(raw_text)
        return ParsedPlanRequest.model_validate(data)

    except Exception:
        return _fallback_parse(text)

def llm_is_configured() -> bool:
    """Return True when an OpenAI API key is available."""
    return bool(os.getenv("OPENAI_API_KEY"))


def explain_plan_with_llm(plan: dict) -> str | None:
    """
    Generate a short explanation for an already validated plan.

    Returns None when no API key is configured or when the model call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5")

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are PlanPilot, an outing-planning assistant. "
                        "Explain why the supplied itinerary is a good match. "
                        "Do not change prices, travel times, venue names, "
                        "or any other validated facts. Keep the explanation concise."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(plan, indent=2),
                },
            ],
        )

        return response.output_text.strip()

    except Exception:
        return None
