from fastapi import FastAPI, HTTPException

from .llm import (
    explain_plan_with_llm,
    llm_is_configured,
    parse_natural_language_request,
)
from .models import (
    NaturalLanguageRequest,
    ParsedPlanRequest,
    PlaceSearchRequest,
    PlanRequest,
)
from .planner import build_plans
from .tools.live_candidates import (
    build_live_venues_with_fallback,
)
from .tools.places import (
    PlaceSearchError,
    geoapify_is_configured,
    search_places,
)


app = FastAPI(
    title="PlanPilot API",
    version="0.4.0",
)


@app.get("/")
def root() -> dict:
    """
    Basic root endpoint confirming that the API is running.
    """
    return {
        "name": "PlanPilot API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    """
    Report the status of the backend and integrations.
    """
    return {
        "status": "ok",
        "llm_configured": llm_is_configured(),
        "places_configured": geoapify_is_configured(),
    }


def parsed_to_plan_request(
    parsed: ParsedPlanRequest,
    payload: NaturalLanguageRequest,
) -> PlanRequest:
    """
    Convert parsed natural-language fields into the PlanRequest
    used by the deterministic itinerary planner.
    """
    must_include: list[str] = []

    if parsed.include_activity:
        must_include.append("activity")

    if parsed.include_dinner:
        must_include.append("dinner")

    if parsed.include_dessert:
        must_include.append("dessert")

    if not must_include:
        must_include = [
            "activity",
            "dinner",
        ]

    allowed_transport = {
        "public_transit",
        "walking",
        "driving",
    }

    transport = (
        parsed.transportation
        if parsed.transportation in allowed_transport
        else "public_transit"
    )

    food_preferences = (
        parsed.food_preferences
        if parsed.food_preferences
        else payload.food_preferences
    )

    return PlanRequest(
        city=parsed.city,
        start_area=payload.start_area,
        date=parsed.date_text or "Friday",
        start_time=parsed.start_time or "17:00",
        budget_total=parsed.budget,
        party_size=parsed.party_size,
        transport=transport,
        vibe=[parsed.vibe],
        must_include=must_include,
        food_preferences=food_preferences,
        max_leg_minutes=parsed.max_travel_minutes,
    )


def serialize_plans(
    request: PlanRequest,
    plans: list,
) -> tuple[list[dict], str | None]:
    """
    Serialize itinerary models and generate an optional explanation.
    """
    serialized = [
        plan.model_dump()
        for plan in plans
    ]

    explanation = explain_plan_with_llm(
        {
            "request": request.model_dump(),
            "plans": serialized,
        }
    )

    return serialized, explanation


@app.post("/plans")
def create_plans(
    request: PlanRequest,
) -> dict:
    """
    Generate itineraries from manually supplied structured fields
    using the original sample venue data.
    """
    plans = build_plans(request)

    serialized, explanation = serialize_plans(
        request=request,
        plans=plans,
    )

    return {
        "request": request.model_dump(),
        "plans": serialized,
        "llm_explanation": explanation,
        "data_notice": (
            "This endpoint currently uses sample venue and "
            "temporary route data."
        ),
    }


@app.post(
    "/parse-request",
    response_model=ParsedPlanRequest,
)
def parse_request(
    payload: NaturalLanguageRequest,
) -> ParsedPlanRequest:
    """
    Parse a natural-language request into structured fields.
    """
    return parse_natural_language_request(
        payload.text
    )


@app.post("/plan-from-text")
def plan_from_text(
    payload: NaturalLanguageRequest,
) -> dict:
    """
    Parse a natural-language request and build plans using
    the sample venue dataset.
    """
    parsed = parse_natural_language_request(
        payload.text
    )

    request = parsed_to_plan_request(
        parsed=parsed,
        payload=payload,
    )

    plans = build_plans(request)

    if not plans:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching plans were found using "
                "the sample venue data."
            ),
        )

    serialized, explanation = serialize_plans(
        request=request,
        plans=plans,
    )

    return {
        "original_text": payload.text,
        "parsed_request": parsed.model_dump(),
        "planning_request": request.model_dump(),
        "plans": serialized,
        "used_live_data": False,
        "llm_explanation": explanation,
        "data_notice": (
            "This endpoint uses sample venue and "
            "temporary route data."
        ),
    }


@app.post("/plan-from-text/live")
def plan_from_text_live(
    payload: NaturalLanguageRequest,
) -> dict:
    """
    Generate itineraries using live Geoapify place candidates.

    If Geoapify is unavailable or returns no results, PlanPilot
    falls back to the original sample venue dataset.
    """
    parsed = parse_natural_language_request(
        payload.text
    )

    request = parsed_to_plan_request(
        parsed=parsed,
        payload=payload,
    )

    venues, used_live_data = (
        build_live_venues_with_fallback(
            request
        )
    )

    plans = build_plans(
        request=request,
        venues=venues,
    )

    if not plans:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching live or fallback plans "
                "were found."
            ),
        )

    serialized, explanation = serialize_plans(
        request=request,
        plans=plans,
    )

    return {
        "original_text": payload.text,
        "parsed_request": parsed.model_dump(),
        "planning_request": request.model_dump(),
        "plans": serialized,
        "used_live_data": used_live_data,
        "venue_candidate_count": len(venues),
        "llm_explanation": explanation,
        "data_notice": (
            "Live Geoapify place candidates were used. "
            "Costs, durations, vibes, and travel times are "
            "currently estimated."
            if used_live_data
            else (
                "Geoapify was unavailable or returned no "
                "candidates, so sample venue data was used."
            )
        ),
    }


@app.post("/places/search")
def search_live_places(
    payload: PlaceSearchRequest,
) -> dict:
    """
    Search Geoapify directly for live places.
    """
    try:
        places = search_places(
            query=payload.query,
            city=payload.city,
            category=payload.category,
            limit=payload.limit,
        )

    except PlaceSearchError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "provider": "geoapify",
        "query": payload.query,
        "city": payload.city,
        "category": payload.category,
        "count": len(places),
        "places": [
            place.model_dump()
            for place in places
        ],
    }
