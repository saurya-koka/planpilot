import json
import os
import re

from dotenv import load_dotenv

from backend.app.models import ParsedPlanRequest

load_dotenv()


def _detect_vibe(text: str) -> str:
    vibe_words = {
        "romantic": [
            "romantic",
            "date",
            "cute",
            "intimate",
        ],
        "fun": [
            "fun",
            "lively",
            "exciting",
            "energetic",
        ],
        "chill": [
            "chill",
            "relaxed",
            "quiet",
            "casual",
        ],
        "fancy": [
            "fancy",
            "upscale",
            "luxury",
            "elegant",
        ],
        "scenic": [
            "scenic",
            "waterfront",
            "view",
            "sunset",
        ],
    }

    for vibe, words in vibe_words.items():
        if any(word in text for word in words):
            return vibe

    return "romantic"


def _detect_date(text: str) -> str | None:
    date_phrases = [
        "next monday",
        "next tuesday",
        "next wednesday",
        "next thursday",
        "next friday",
        "next saturday",
        "next sunday",
        "this monday",
        "this tuesday",
        "this wednesday",
        "this thursday",
        "this friday",
        "this saturday",
        "this sunday",
        "today",
        "tonight",
        "tomorrow",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    for phrase in date_phrases:
        if phrase in text:
            return phrase.title()

    return None


def _detect_food_preferences(text: str) -> list[str]:
    preferences: list[str] = []

    food_patterns = {
        "chicken options": [
            "chicken",
            "only eats chicken",
            "chicken dishes",
            "chicken options",
        ],
        "risotto": [
            "risotto",
        ],
        "vegetarian": [
            "vegetarian",
            "meat-free",
            "no meat",
        ],
        "vegan": [
            "vegan",
            "plant-based",
        ],
        "gluten-free": [
            "gluten free",
            "gluten-free",
            "no gluten",
        ],
        "halal": [
            "halal",
        ],
        "kosher": [
            "kosher",
        ],
        "seafood": [
            "seafood",
            "fish",
            "sushi",
        ],
    }

    for preference, patterns in food_patterns.items():
        if any(pattern in text for pattern in patterns):
            preferences.append(preference)

    return preferences


def _detect_transportation(text: str) -> str:
    if any(
        phrase in text
        for phrase in [
            "no car",
            "public transit",
            "public transportation",
            "train",
            "subway",
            "metro",
            "bus",
            "commuter rail",
        ]
    ):
        return "public_transit"

    if any(
        phrase in text
        for phrase in [
            "walking only",
            "walkable",
            "on foot",
        ]
    ):
        return "walking"

    if any(
        phrase in text
        for phrase in [
            "driving",
            "we have a car",
            "by car",
        ]
    ):
        return "driving"

    return "public_transit"


def _fallback_parse(text: str) -> ParsedPlanRequest:
    lowered = text.lower()

    budget_match = re.search(
        r"(?:under|below|max(?:imum)?|budget(?: of)?|up to)"
        r"\s*\$?(\d+(?:\.\d+)?)",
        lowered,
    )

    people_match = re.search(
        r"(?:for|party of)\s+(\d+)\s+"
        r"(?:people|persons?|guests?)",
        lowered,
    )

    travel_match = re.search(
        r"(?:under|max(?:imum)?|within|no more than)"
        r"\s+(\d+)\s+minutes?",
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
        "Portland",
        "Newport",
        "Cambridge",
        "Somerville",
    ]

    for candidate in common_cities:
        if candidate.lower() in lowered:
            city = candidate
            break

    include_activity = any(
        word in lowered
        for word in [
            "activity",
            "karaoke",
            "movie",
            "museum",
            "bowling",
            "game",
            "concert",
            "show",
            "mini golf",
            "photo booth",
        ]
    )

    include_dinner = any(
        word in lowered
        for word in [
            "dinner",
            "restaurant",
            "food",
            "eat",
            "meal",
        ]
    )

    include_dessert = any(
        word in lowered
        for word in [
            "dessert",
            "ice cream",
            "bakery",
            "sweets",
            "cake",
            "pastry",
        ]
    )

    # A general "date" request usually implies at least one activity.
    if "date" in lowered and not (
        include_activity
        or include_dinner
        or include_dessert
    ):
        include_activity = True
        include_dinner = True

    return ParsedPlanRequest(
        city=city,
        budget=(
            float(budget_match.group(1))
            if budget_match
            else 200
        ),
        party_size=(
            int(people_match.group(1))
            if people_match
            else 2
        ),
        max_travel_minutes=(
            int(travel_match.group(1))
            if travel_match
            else 30
        ),
        vibe=_detect_vibe(lowered),
        include_activity=include_activity,
        include_dinner=include_dinner,
        include_dessert=include_dessert,
        transportation=_detect_transportation(lowered),
        start_time=(
            time_match.group(1).upper()
            if time_match
            else None
        ),
        date_text=_detect_date(lowered),
        food_preferences=_detect_food_preferences(lowered),
    )


def parse_natural_language_request(
    text: str,
) -> ParsedPlanRequest:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return _fallback_parse(text)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5",
        )

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Extract outing-planning requirements "
                        "from the user's message. Return only "
                        "valid JSON with exactly these keys: "
                        "city, budget, party_size, "
                        "max_travel_minutes, vibe, "
                        "include_activity, include_dinner, "
                        "include_dessert, transportation, "
                        "start_time, date_text, "
                        "food_preferences. "
                        "transportation must be one of "
                        "public_transit, walking, or driving. "
                        "food_preferences must be a JSON list "
                        "such as ['chicken options', 'risotto']. "
                        "Use sensible defaults when details "
                        "are missing. Do not include markdown "
                        "or any explanation outside the JSON."
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
    """
    Return True when an OpenAI API key is available.
    """
    return bool(os.getenv("OPENAI_API_KEY"))


def explain_plan_with_llm(
    plan: dict,
) -> str | None:
    """
    Generate a concise explanation for validated plans.

    Returns None when no API key is configured or when
    the model call fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5",
        )

        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are PlanPilot, an outing-planning "
                        "assistant. Explain why the supplied "
                        "itinerary options match the user's "
                        "request. Do not change venue names, "
                        "prices, travel times, durations, or "
                        "any other validated facts. Keep the "
                        "explanation concise and practical."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        plan,
                        indent=2,
                    ),
                },
            ],
        )

        return response.output_text.strip()

    except Exception:
        return None
