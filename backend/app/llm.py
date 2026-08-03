from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv

from backend.app.models import ParsedPlanRequest

load_dotenv()


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


VIBE_PATTERNS = {
    "romantic": [
        "romantic",
        "date",
        "date night",
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
        "laid back",
        "laid-back",
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
        "beautiful views",
    ],
    "active": [
        "active",
        "adventure",
        "adventurous",
        "outdoor",
        "outdoors",
        "sports",
        "physical",
    ],
    "cultural": [
        "cultural",
        "culture",
        "art",
        "historic",
        "history",
        "museum",
        "gallery",
    ],
    "nightlife": [
        "nightlife",
        "night out",
        "party",
        "club",
        "bar hopping",
        "late night",
    ],
    "family": [
        "family",
        "family friendly",
        "family-friendly",
        "kids",
        "children",
    ],
    "foodie": [
        "foodie",
        "food focused",
        "food-focused",
        "food tour",
        "culinary",
        "tasting",
    ],
    "budget": [
        "budget",
        "cheap",
        "affordable",
        "low cost",
        "low-cost",
        "inexpensive",
    ],
    "rainy-day": [
        "rainy day",
        "rainy-day",
        "raining",
        "rainy",
        "bad weather",
        "indoors only",
        "indoor only",
    ],
    "work-friendly": [
        "work friendly",
        "work-friendly",
        "study",
        "working",
        "laptop",
        "wifi",
        "wi-fi",
    ],
    "group": [
        "group",
        "friends",
        "friend group",
        "group outing",
    ],
}


def _clean_text(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )
    return cleaned


def _contains_phrase(
    text: str,
    phrase: str,
) -> bool:
    """
    Match a phrase while avoiding partial-word matches.
    """
    pattern = (
        r"(?<!\w)"
        + re.escape(phrase)
        + r"(?!\w)"
    )

    return bool(
        re.search(
            pattern,
            text,
        )
    )


def _detect_vibes(
    text: str,
    party_size: int,
    budget: float,
) -> list[str]:
    """
    Extract every relevant outing intent.
    """
    detected: list[str] = []

    for vibe, patterns in VIBE_PATTERNS.items():
        if any(
            _contains_phrase(
                text,
                pattern,
            )
            for pattern in patterns
        ):
            detected.append(vibe)

    if party_size >= 4:
        detected.append("group")

    if budget <= 80:
        detected.append("budget")

    if not detected:
        detected.append("fun")

    return list(
        dict.fromkeys(detected)
    )


def _detect_party_size(
    text: str,
) -> int:
    """
    Detect numeric and written party sizes.

    Examples:
        for 5 people
        for five people
        party of 4
        group of six
        me and four friends
    """
    numeric_match = re.search(
        r"(?:for|party of|group of)\s+"
        r"(\d+)\s*"
        r"(?:people|persons?|guests?|friends?)?",
        text,
    )

    if numeric_match:
        value = int(
            numeric_match.group(1)
        )

        return min(
            max(value, 1),
            12,
        )

    number_words_pattern = "|".join(
        NUMBER_WORDS.keys()
    )

    word_match = re.search(
        rf"(?:for|party of|group of)\s+"
        rf"({number_words_pattern})\s*"
        r"(?:people|persons?|guests?|friends?)?",
        text,
    )

    if word_match:
        return NUMBER_WORDS[
            word_match.group(1)
        ]

    friends_match = re.search(
        rf"\b({number_words_pattern}|\d+)\s+"
        r"friends?\b",
        text,
    )

    if friends_match:
        raw_value = friends_match.group(1)

        friend_count = (
            int(raw_value)
            if raw_value.isdigit()
            else NUMBER_WORDS[raw_value]
        )

        if any(
            phrase in text
            for phrase in [
                "me and",
                "myself and",
                "i and",
            ]
        ):
            friend_count += 1

        return min(
            max(friend_count, 1),
            12,
        )

    return 2


def _detect_date(
    text: str,
) -> str | None:
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


def _detect_food_preferences(
    text: str,
) -> list[str]:
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
            "meat free",
            "no meat",
        ],
        "vegan": [
            "vegan",
            "plant-based",
            "plant based",
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
        "indian": [
            "indian food",
            "indian restaurant",
            "biryani",
            "curry",
        ],
        "chinese": [
            "chinese food",
            "chinese restaurant",
            "dim sum",
        ],
        "thai": [
            "thai food",
            "thai restaurant",
            "pad thai",
        ],
        "mexican": [
            "mexican food",
            "mexican restaurant",
            "tacos",
            "taco",
        ],
    }

    for preference, patterns in food_patterns.items():
        if any(
            pattern in text
            for pattern in patterns
        ):
            preferences.append(
                preference
            )

    return preferences


def _detect_transportation(
    text: str,
) -> str:
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


def _detect_city(
    text: str,
) -> str:
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
        if candidate.lower() in text:
            return candidate

    return "Boston"


def _fallback_parse(
    text: str,
) -> ParsedPlanRequest:
    lowered = _clean_text(text)

    budget_match = re.search(
        r"(?:under|below|max(?:imum)?|budget(?: of)?|up to)"
        r"\s*\$?(\d+(?:\.\d+)?)",
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

    budget = (
        float(budget_match.group(1))
        if budget_match
        else 200
    )

    party_size = _detect_party_size(
        lowered
    )

    include_activity = any(
        word in lowered
        for word in [
            "activity",
            "outing",
            "karaoke",
            "movie",
            "museum",
            "bowling",
            "game",
            "concert",
            "show",
            "mini golf",
            "photo booth",
            "park",
            "gallery",
            "cinema",
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
            "lunch",
            "brunch",
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
            "gelato",
            "chocolate",
        ]
    )

    if "date" in lowered and not (
        include_activity
        or include_dinner
        or include_dessert
    ):
        include_activity = True
        include_dinner = True

    if "outing" in lowered and not (
        include_activity
        or include_dinner
        or include_dessert
    ):
        include_activity = True
        include_dinner = True

    return ParsedPlanRequest(
        city=_detect_city(lowered),
        budget=budget,
        party_size=party_size,
        max_travel_minutes=(
            int(travel_match.group(1))
            if travel_match
            else 30
        ),
        vibes=_detect_vibes(
            text=lowered,
            party_size=party_size,
            budget=budget,
        ),
        include_activity=include_activity,
        include_dinner=include_dinner,
        include_dessert=include_dessert,
        transportation=(
            _detect_transportation(lowered)
        ),
        start_time=(
            time_match.group(1).upper()
            if time_match
            else None
        ),
        date_text=_detect_date(lowered),
        food_preferences=(
            _detect_food_preferences(
                lowered
            )
        ),
    )


def parse_natural_language_request(
    text: str,
) -> ParsedPlanRequest:
    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        return _fallback_parse(text)

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key
        )

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
                        "max_travel_minutes, vibes, "
                        "include_activity, include_dinner, "
                        "include_dessert, transportation, "
                        "start_time, date_text, "
                        "food_preferences. "
                        "vibes must be a JSON list and may "
                        "contain multiple applicable intents, "
                        "such as ['chill', 'rainy-day'] or "
                        "['fun', 'group']. Supported intents "
                        "include romantic, fun, chill, fancy, "
                        "scenic, active, cultural, nightlife, "
                        "family, foodie, budget, rainy-day, "
                        "work-friendly, and group. "
                        "Infer group when party_size is 4 or "
                        "greater. transportation must be one "
                        "of public_transit, walking, or driving. "
                        "food_preferences must be a JSON list. "
                        "Use sensible defaults when details "
                        "are missing. Do not include markdown "
                        "or explanation outside the JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
        )

        raw_text = (
            response.output_text.strip()
        )

        data = json.loads(
            raw_text
        )

        validated = (
            ParsedPlanRequest.model_validate(
                data
            )
        )

        fallback = _fallback_parse(
            text
        )

        validated.vibes = list(
            dict.fromkeys(
                [
                    *validated.vibes,
                    *fallback.vibes,
                ]
            )
        )

        if fallback.party_size != 2:
            validated.party_size = (
                fallback.party_size
            )

        if fallback.food_preferences:
            validated.food_preferences = list(
                dict.fromkeys(
                    [
                        *validated.food_preferences,
                        *fallback.food_preferences,
                    ]
                )
            )

        return validated

    except Exception:
        return _fallback_parse(text)


def llm_is_configured() -> bool:
    """
    Return True when an OpenAI API key is available.
    """
    return bool(
        os.getenv("OPENAI_API_KEY")
    )


def explain_plan_with_llm(
    plan: dict,
) -> str | None:
    """
    Generate a concise explanation for validated plans.

    Returns None when no API key is configured or when the model
    call fails.
    """
    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key
        )

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
                        "other validated facts. Keep the "
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

        return (
            response.output_text.strip()
        )

    except Exception:
        return None
