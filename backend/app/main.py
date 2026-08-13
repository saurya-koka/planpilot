from __future__ import annotations

from typing import Any

from fastapi import (
    FastAPI,
    HTTPException,
)

from .agent_controller import (
    agent_is_configured,
    run_agent,
)
from .graph_orchestrator import (
    run_planpilot_graph,
)
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
from .planner import (
    build_plans,
)
from .tools.live_candidates import (
    build_live_venues_with_fallback,
)
from .tools.places import (
    PlaceSearchError,
    geocode_location,
    geoapify_is_configured,
    search_places,
)
from .tools.routing import (
    haversine_distance_km,
)


app = FastAPI(
    title="PlanPilot API",
    version="0.8.0",
)


@app.get("/")
def root() -> dict[str, str]:
    """
    Confirm that the PlanPilot API is running.
    """

    return {
        "name": "PlanPilot API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[
    str,
    bool | str,
]:
    """
    Report backend and integration status.
    """

    return {
        "status": "ok",
        "llm_configured": (
            llm_is_configured()
        ),
        "agent_configured": (
            agent_is_configured()
        ),
        "places_configured": (
            geoapify_is_configured()
        ),
        "langgraph_enabled": True,
    }


def parsed_to_plan_request(
    parsed: ParsedPlanRequest,
    payload: NaturalLanguageRequest,
) -> PlanRequest:
    """
    Convert parsed natural-language fields into the structured
    PlanRequest used by the deterministic planner.
    """

    must_include: list[
        str
    ] = []

    if parsed.include_activity:
        must_include.append(
            "activity"
        )

    if parsed.include_dinner:
        must_include.append(
            "dinner"
        )

    if parsed.include_dessert:
        must_include.append(
            "dessert"
        )

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
        if (
            parsed.transportation
            in allowed_transport
        )
        else "public_transit"
    )

    food_preferences = (
        parsed.food_preferences
        if parsed.food_preferences
        else payload.food_preferences
    )

    return PlanRequest(
        city=parsed.city,
        start_area=(
            payload.start_area
        ),
        date=(
            parsed.date_text
            or "Friday"
        ),
        start_time=(
            parsed.start_time
            or "17:00"
        ),
        budget_total=(
            parsed.budget
        ),
        party_size=(
            parsed.party_size
        ),
        transport=transport,
        vibe=parsed.vibes,
        must_include=(
            must_include
        ),
        food_preferences=(
            food_preferences
        ),
        max_leg_minutes=(
            parsed
            .max_travel_minutes
        ),
    )


def serialize_plans(
    request: PlanRequest,
    plans: list[Any],
) -> tuple[
    list[
        dict[
            str,
            Any,
        ]
    ],
    str | None,
]:
    """
    Serialize itinerary models and generate an optional
    natural-language explanation.
    """

    serialized = [
        plan.model_dump()
        for plan
        in plans
    ]

    explanation = (
        explain_plan_with_llm(
            {
                "request": (
                    request.model_dump()
                ),
                "plans": serialized,
            }
        )
    )

    return (
        serialized,
        explanation,
    )


def geocode_start_area(
    request: PlanRequest,
) -> tuple[
    float,
    float,
] | None:
    """
    Geocode the user's starting area and reject obviously incorrect
    matches that are far outside the requested city's metro area.
    """

    try:
        candidate_coordinates = (
            geocode_location(
                (
                    f"{request.start_area}, "
                    "Massachusetts, USA"
                )
            )
        )

        city_coordinates = (
            geocode_location(
                (
                    f"{request.city}, "
                    "Massachusetts, USA"
                ),
                location_type="city",
            )
        )

        distance_from_city = (
            haversine_distance_km(
                latitude_a=(
                    candidate_coordinates[
                        0
                    ]
                ),
                longitude_a=(
                    candidate_coordinates[
                        1
                    ]
                ),
                latitude_b=(
                    city_coordinates[
                        0
                    ]
                ),
                longitude_b=(
                    city_coordinates[
                        1
                    ]
                ),
            )
        )

        if (
            distance_from_city
            > 60
        ):
            return None

        return (
            candidate_coordinates
        )

    except PlaceSearchError:
        return None


def serialize_start_coordinates(
    coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ),
) -> (
    dict[
        str,
        float,
    ]
    | None
):
    """
    Convert internal coordinate tuple into API-friendly JSON.
    """

    if coordinates is None:
        return None

    return {
        "latitude": (
            coordinates[0]
        ),
        "longitude": (
            coordinates[1]
        ),
    }


@app.post("/plans")
def create_plans(
    request: PlanRequest,
) -> dict[
    str,
    Any,
]:
    """
    Generate itineraries from manually supplied structured fields.
    """

    plans = build_plans(
        request=request,
    )

    serialized, explanation = (
        serialize_plans(
            request=request,
            plans=plans,
        )
    )

    return {
        "request": (
            request.model_dump()
        ),
        "plans": serialized,
        "used_live_data": False,
        "start_coordinates": None,
        "llm_explanation": (
            explanation
        ),
        "data_notice": (
            "This endpoint currently "
            "uses sample venue data."
        ),
    }


@app.post(
    "/parse-request",
    response_model=(
        ParsedPlanRequest
    ),
)
def parse_request(
    payload: NaturalLanguageRequest,
) -> ParsedPlanRequest:
    """
    Parse natural language into structured fields.
    """

    return (
        parse_natural_language_request(
            payload.text
        )
    )


@app.post(
    "/plan-from-text"
)
def plan_from_text(
    payload: NaturalLanguageRequest,
) -> dict[
    str,
    Any,
]:
    """
    Parse natural language and build plans using sample venue data.
    """

    parsed = (
        parse_natural_language_request(
            payload.text
        )
    )

    request = (
        parsed_to_plan_request(
            parsed=parsed,
            payload=payload,
        )
    )

    plans = build_plans(
        request=request,
    )

    if not plans:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching plans were "
                "found using the sample "
                "venue data."
            ),
        )

    serialized, explanation = (
        serialize_plans(
            request=request,
            plans=plans,
        )
    )

    return {
        "original_text": (
            payload.text
        ),
        "parsed_request": (
            parsed.model_dump()
        ),
        "planning_request": (
            request.model_dump()
        ),
        "plans": serialized,
        "used_live_data": False,
        "start_coordinates": None,
        "llm_explanation": (
            explanation
        ),
        "data_notice": (
            "This endpoint uses "
            "sample venue data."
        ),
    }


@app.post(
    "/plan-from-text/live"
)
def plan_from_text_live(
    payload: NaturalLanguageRequest,
) -> dict[
    str,
    Any,
]:
    """
    Generate itineraries using live Geoapify candidates.
    """

    parsed = (
        parse_natural_language_request(
            payload.text
        )
    )

    request = (
        parsed_to_plan_request(
            parsed=parsed,
            payload=payload,
        )
    )

    (
        venues,
        used_live_data,
    ) = (
        build_live_venues_with_fallback(
            request
        )
    )

    start_coordinates = (
        geocode_start_area(
            request
        )
    )

    plans = build_plans(
        request=request,
        venues=venues,
        start_coordinates=(
            start_coordinates
        ),
    )

    if not plans:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching live or "
                "fallback plans were "
                "found."
            ),
        )

    serialized, explanation = (
        serialize_plans(
            request=request,
            plans=plans,
        )
    )

    return {
        "original_text": (
            payload.text
        ),
        "parsed_request": (
            parsed.model_dump()
        ),
        "planning_request": (
            request.model_dump()
        ),
        "plans": serialized,
        "used_live_data": (
            used_live_data
        ),
        "venue_candidate_count": (
            len(venues)
        ),
        "start_coordinates": (
            serialize_start_coordinates(
                start_coordinates
            )
        ),
        "llm_explanation": (
            explanation
        ),
        "data_notice": (
            (
                "Live Geoapify place "
                "candidates and routing "
                "were used. Costs, "
                "durations, and vibes "
                "remain estimates."
            )
            if used_live_data
            else (
                "Geoapify place search "
                "was unavailable or "
                "returned no candidates, "
                "so fallback venue data "
                "was used."
            )
        ),
    }


@app.post(
    "/agent/plan-from-text"
)
def agent_plan_from_text(
    payload: NaturalLanguageRequest,
) -> dict[
    str,
    Any,
]:
    """
    Run the V2.5 LLM tool-calling controller.
    """

    parsed = (
        parse_natural_language_request(
            payload.text
        )
    )

    request = (
        parsed_to_plan_request(
            parsed=parsed,
            payload=payload,
        )
    )

    (
        venues,
        used_live_data,
    ) = (
        build_live_venues_with_fallback(
            request
        )
    )

    start_coordinates = (
        geocode_start_area(
            request
        )
    )

    result = run_agent(
        user_message=(
            payload.text
        ),
        request=request,
        venues=venues,
        start_coordinates=(
            start_coordinates
        ),
    )

    if not result.final_plans:
        raise HTTPException(
            status_code=404,
            detail=(
                "The PlanPilot agent "
                "could not produce an "
                "itinerary."
            ),
        )

    return {
        "original_text": (
            payload.text
        ),
        "parsed_request": (
            parsed.model_dump()
        ),
        "planning_request": (
            request.model_dump()
        ),
        "agent_configured": (
            agent_is_configured()
        ),
        "agent_success": (
            result.success
        ),
        "agent_exhausted": (
            result.exhausted
        ),
        "agent_message": (
            result.final_message
        ),
        "agent_step_count": (
            len(result.steps)
        ),
        "agent_steps": [
            step.model_dump()
            for step
            in result.steps
        ],
        "plans": [
            plan.model_dump()
            for plan
            in result.final_plans
        ],
        "used_live_data": (
            used_live_data
        ),
        "venue_candidate_count": (
            len(venues)
        ),
        "start_coordinates": (
            serialize_start_coordinates(
                start_coordinates
            )
        ),
        "data_notice": (
            (
                "The LLM controller "
                "orchestrated structured "
                "PlanPilot tools over "
                "live venue candidates."
            )
            if (
                agent_is_configured()
                and used_live_data
            )
            else (
                "PlanPilot used its "
                "deterministic fallback "
                "when live LLM or venue "
                "services were not "
                "available."
            )
        ),
    }


@app.post(
    "/graph/plan-from-text"
)
def graph_plan_from_text(
    payload: NaturalLanguageRequest,
) -> dict[
    str,
    Any,
]:
    """
    Run the V2.6 LangGraph orchestration workflow.

    The graph owns deterministic control flow across planning,
    validation, repair, live venue search, replanning, and finish.
    """

    parsed = (
        parse_natural_language_request(
            payload.text
        )
    )

    request = (
        parsed_to_plan_request(
            parsed=parsed,
            payload=payload,
        )
    )

    (
        venues,
        used_live_data,
    ) = (
        build_live_venues_with_fallback(
            request
        )
    )

    start_coordinates = (
        geocode_start_area(
            request
        )
    )

    result = (
        run_planpilot_graph(
            user_message=(
                payload.text
            ),
            request=request,
            venues=venues,
            start_coordinates=(
                start_coordinates
            ),
            max_iterations=4,
        )
    )

    plans = result.get(
        "plans",
        [],
    )

    if not plans:
        raise HTTPException(
            status_code=404,
            detail=(
                "The LangGraph workflow "
                "could not produce an "
                "itinerary candidate."
            ),
        )

    return {
        "original_text": (
            payload.text
        ),
        "parsed_request": (
            parsed.model_dump()
        ),
        "planning_request": (
            request.model_dump()
        ),
        "graph_success": (
            result.get(
                "has_usable_plan",
                False,
            )
        ),
        "graph_exhausted": (
            result.get(
                "exhausted",
                False,
            )
        ),
        "graph_message": (
            result.get(
                "final_message",
                "",
            )
        ),
        "graph_iterations": (
            result.get(
                "iteration_count",
                0,
            )
        ),
        "graph_search_count": (
            result.get(
                "search_count",
                0,
            )
        ),
        "searched_categories": (
            result.get(
                "searched_categories",
                [],
            )
        ),
        "last_action": (
            result.get(
                "last_action",
                "",
            )
        ),
        "plans": [
            plan.model_dump()
            for plan
            in plans
        ],
        "used_live_data": (
            used_live_data
        ),
        "venue_candidate_count": (
            len(
                result.get(
                    "venues",
                    venues,
                )
            )
        ),
        "start_coordinates": (
            serialize_start_coordinates(
                start_coordinates
            )
        ),
        "data_notice": (
            "LangGraph orchestrated "
            "PlanPilot planning, "
            "validation, repair, venue "
            "search, and replanning."
        ),
    }


@app.post(
    "/places/search"
)
def search_live_places(
    payload: PlaceSearchRequest,
) -> dict[
    str,
    Any,
]:
    """
    Search Geoapify directly for live places.
    """

    try:
        places = search_places(
            query=payload.query,
            city=payload.city,
            category=(
                payload.category
            ),
            limit=payload.limit,
        )

    except PlaceSearchError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(
                exc
            ),
        ) from exc

    return {
        "provider": "geoapify",
        "query": payload.query,
        "city": payload.city,
        "category": (
            payload.category
        ),
        "count": len(
            places
        ),
        "places": [
            place.model_dump()
            for place
            in places
        ],
    }
