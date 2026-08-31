from __future__ import annotations

from typing import Any

from mcp.server import (
    MCPServer,
)

from .graph_orchestrator import (
    run_planpilot_graph,
)
from .live_weather import (
    OpenMeteoWeatherProvider,
)
from .llm import (
    parse_natural_language_request,
)
from .main import (
    geocode_start_area,
    parsed_to_plan_request,
    serialize_start_coordinates,
)
from .models import (
    NaturalLanguageRequest,
)
from .tools.live_candidates import (
    build_live_venues_with_fallback,
)
from .tools.places import (
    PlaceSearchError,
    search_places,
)
from .weather import (
    assess_weather,
)


mcp = MCPServer(
    "PlanPilot"
)


@mcp.tool()
def parse_trip_request(
    text: str,
) -> dict[str, Any]:
    """
    Parse a natural-language travel or date-plan request into
    PlanPilot's structured representation.
    """

    parsed = (
        parse_natural_language_request(
            text
        )
    )

    return parsed.model_dump()


@mcp.tool()
def search_planpilot_places(
    query: str,
    city: str,
    category: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Search PlanPilot's live place provider.
    """

    if limit < 1:
        raise ValueError(
            "limit must be at least 1."
        )

    if limit > 20:
        limit = 20

    try:
        places = search_places(
            query=query,
            city=city,
            category=category,
            limit=limit,
        )

    except PlaceSearchError as exc:
        return {
            "success": False,
            "provider": "geoapify",
            "query": query,
            "city": city,
            "count": 0,
            "places": [],
            "error": str(
                exc
            ),
        }

    return {
        "success": True,
        "provider": "geoapify",
        "query": query,
        "city": city,
        "count": len(
            places
        ),
        "places": [
            place.model_dump()
            for place
            in places
        ],
    }


@mcp.tool()
def check_planpilot_weather(
    city: str,
    date: str,
    start_time: str = "18:00",
) -> dict[str, Any]:
    """
    Retrieve a live weather forecast and classify itinerary risk.
    """

    provider = (
        OpenMeteoWeatherProvider()
    )

    snapshot = (
        provider.get_weather(
            city=city,
            date=date,
            start_time=start_time,
        )
    )

    assessment = (
        assess_weather(
            snapshot
        )
    )

    return {
        "condition": (
            snapshot.condition
        ),
        "temperature_c": (
            snapshot.temperature_c
        ),
        "precipitation_probability": (
            snapshot
            .precipitation_probability
        ),
        "wind_speed_kph": (
            snapshot.wind_speed_kph
        ),
        "severe_weather": (
            snapshot.severe_weather
        ),
        "source": (
            snapshot.source
        ),
        "risk_level": (
            assessment
            .risk_level
            .value
        ),
        "outdoor_safe": (
            assessment.outdoor_safe
        ),
        "reasons": list(
            assessment.reasons
        ),
    }


@mcp.tool()
def plan_itinerary(
    text: str,
    start_area: str = "Davis Square",
    food_preferences: (
        list[str]
        | None
    ) = None,
    max_iterations: int = 4,
) -> dict[str, Any]:
    """
    Run PlanPilot's complete agentic itinerary workflow.

    Pipeline:

        natural-language request
            ->
        structured parsing
            ->
        start-area geocoding
            ->
        live venue candidate retrieval
            ->
        weather assessment
            ->
        weather-aware venue adaptation
            ->
        hybrid RAG retrieval
            ->
        LangGraph planning
            ->
        validation / repair
            ->
        final itinerary candidates

    This is the primary high-level PlanPilot MCP tool.
    """

    if max_iterations < 1:
        raise ValueError(
            "max_iterations must be at least 1."
        )

    if max_iterations > 10:
        max_iterations = 10

    payload = (
        NaturalLanguageRequest(
            text=text,
            start_area=start_area,
            food_preferences=(
                food_preferences
                or []
            ),
        )
    )

    parsed = (
        parse_natural_language_request(
            text
        )
    )

    request = (
        parsed_to_plan_request(
            parsed=parsed,
            payload=payload,
        )
    )

    start_coordinates = (
        geocode_start_area(
            request
        )
    )

    (
        venues,
        used_live_data,
    ) = (
        build_live_venues_with_fallback(
            request=request,
            start_coordinates=(
                start_coordinates
            ),
        )
    )

    result = (
        run_planpilot_graph(
            user_message=text,
            request=request,
            venues=venues,
            start_coordinates=(
                start_coordinates
            ),
            max_iterations=(
                max_iterations
            ),
        )
    )

    plans = result.get(
        "plans",
        [],
    )

    if not plans:
        return {
            "success": False,
            "message": (
                "PlanPilot could not produce "
                "an itinerary candidate."
            ),
            "planning_request": (
                request.model_dump()
            ),
            "plans": [],
            "graph_exhausted": (
                result.get(
                    "exhausted",
                    False,
                )
            ),
        }

    return {
        "success": (
            result.get(
                "has_usable_plan",
                False,
            )
        ),
        "original_text": text,
        "planning_request": (
            request.model_dump()
        ),
        "start_coordinates": (
            serialize_start_coordinates(
                start_coordinates
            )
        ),
        "used_live_data": (
            used_live_data
        ),
        "venue_candidate_count": len(
            result.get(
                "venues",
                venues,
            )
        ),

        # LangGraph metadata.
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

        # Hybrid RAG metadata.
        "rag_used": (
            result.get(
                "rag_used",
                False,
            )
        ),
        "rag_result_count": (
            result.get(
                "rag_result_count",
                0,
            )
        ),
        "rag_ranked_venue_names": (
            result.get(
                "rag_ranked_venue_names",
                [],
            )
        ),

        # Weather metadata.
        "weather_checked": (
            result.get(
                "weather_checked",
                False,
            )
        ),
        "weather_condition": (
            result.get(
                "weather_condition",
                "",
            )
        ),
        "weather_risk_level": (
            result.get(
                "weather_risk_level",
                "",
            )
        ),
        "weather_outdoor_safe": (
            result.get(
                "weather_outdoor_safe",
                True,
            )
        ),
        "weather_adjusted": (
            result.get(
                "weather_adjusted",
                False,
            )
        ),
        "weather_removed_venue_names": (
            result.get(
                "weather_removed_venue_names",
                [],
            )
        ),

        "plans": [
            plan.model_dump()
            for plan
            in plans
        ],
    }


@mcp.resource(
    "planpilot://capabilities"
)
def planpilot_capabilities() -> str:
    """
    Describe the PlanPilot MCP surface.
    """

    return (
        "PlanPilot MCP capabilities:\n"
        "- Parse natural-language planning requests\n"
        "- Search live venue candidates\n"
        "- Retrieve and assess live weather\n"
        "- Generate complete weather-aware itineraries\n"
        "- Run hybrid RAG ranking\n"
        "- Run LangGraph validation and repair"
    )


def main() -> None:
    """
    Run PlanPilot as an MCP server.

    Transport is selected using PLANPILOT_MCP_TRANSPORT.

    Supported values:
        stdio
        streamable-http
    """

    import os

    transport = (
        os.getenv(
            "PLANPILOT_MCP_TRANSPORT",
            "stdio",
        )
        .strip()
        .lower()
    )

    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8001,
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
        )
        return

    if transport != "stdio":
        raise ValueError(
            "PLANPILOT_MCP_TRANSPORT must be "
            "'stdio' or 'streamable-http'."
        )

    mcp.run(
        transport="stdio"
    )


if __name__ == "__main__":
    main()
