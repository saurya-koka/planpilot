from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from .agent_models import (
    AgentToolCall,
    AgentToolName,
    ToolExecutionRecord,
    parse_tool_arguments,
)
from .models import (
    Itinerary,
    PlaceResult,
    PlanRequest,
    Venue,
)
from .planner import (
    build_plans,
)
from .repair import (
    repair_itinerary,
)
from .tools.places import (
    PlaceSearchError,
    search_places,
)
from .validator import (
    validate_itinerary,
)


# ---------------------------------------------------------------
# PLANPILOT -> GEOAPIFY CATEGORY TRANSLATION
# ---------------------------------------------------------------

AGENT_SEARCH_CATEGORY_MAP = {
    "activity": "entertainment",
    "restaurant": "catering.restaurant",
    "dessert": "catering",
}


# ---------------------------------------------------------------
# OPENAI STRICT FUNCTION DEFINITIONS
# ---------------------------------------------------------------

SEARCH_VENUES_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "search_venues",
    "description": (
        "Search for real venue candidates in a city. "
        "Use this when additional activity, restaurant, or dessert "
        "options are needed."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Natural-language venue search query, such as "
                    "'affordable Italian restaurant' or "
                    "'indoor activity'."
                ),
            },
            "city": {
                "type": "string",
                "description": (
                    "City in which to search."
                ),
            },
            "category": {
                "type": "string",
                "enum": [
                    "activity",
                    "restaurant",
                    "dessert",
                ],
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": [
            "query",
            "city",
            "category",
            "limit",
        ],
        "additionalProperties": False,
    },
}


BUILD_PLANS_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "build_plans",
    "description": (
        "Generate itinerary candidates from a fully structured "
        "PlanPilot request."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "request": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                    },
                    "start_area": {
                        "type": "string",
                    },
                    "date": {
                        "type": "string",
                    },
                    "start_time": {
                        "type": "string",
                    },
                    "budget_total": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                    },
                    "party_size": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 12,
                    },
                    "transport": {
                        "type": "string",
                        "enum": [
                            "public_transit",
                            "walking",
                            "driving",
                        ],
                    },
                    "vibe": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "must_include": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "food_preferences": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "max_leg_minutes": {
                        "type": "integer",
                        "minimum": 5,
                        "maximum": 180,
                    },
                },
                "required": [
                    "city",
                    "start_area",
                    "date",
                    "start_time",
                    "budget_total",
                    "party_size",
                    "transport",
                    "vibe",
                    "must_include",
                    "food_preferences",
                    "max_leg_minutes",
                ],
                "additionalProperties": False,
            },
        },
        "required": [
            "request",
        ],
        "additionalProperties": False,
    },
}


VALIDATE_PLAN_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "validate_plan",
    "description": (
        "Validate one itinerary candidate against the current "
        "planning request. Use the zero-based plan index."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "plan_index": {
                "type": "integer",
                "minimum": 0,
            },
        },
        "required": [
            "plan_index",
        ],
        "additionalProperties": False,
    },
}


REPAIR_PLAN_TOOL: dict[str, Any] = {
    "type": "function",
    "name": "repair_plan",
    "description": (
        "Run PlanPilot's bounded repair loop on one itinerary "
        "candidate that contains hard validation errors."
    ),
    "strict": True,
    "parameters": {
        "type": "object",
        "properties": {
            "plan_index": {
                "type": "integer",
                "minimum": 0,
            },
            "max_attempts": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
            },
        },
        "required": [
            "plan_index",
            "max_attempts",
        ],
        "additionalProperties": False,
    },
}


OPENAI_AGENT_TOOLS: list[
    dict[str, Any]
] = [
    SEARCH_VENUES_TOOL,
    BUILD_PLANS_TOOL,
    VALIDATE_PLAN_TOOL,
    REPAIR_PLAN_TOOL,
]


# ---------------------------------------------------------------
# AGENT WORKING CONTEXT
# ---------------------------------------------------------------


@dataclass
class AgentToolContext:
    """
    Python-owned working memory for one LLM agent run.
    """

    request: PlanRequest

    venue_source: list[
        Venue
    ] = field(
        default_factory=list,
    )

    plans: list[
        Itinerary
    ] = field(
        default_factory=list,
    )

    start_coordinates: (
        tuple[float, float]
        | None
    ) = None


# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------


def get_plan_by_index(
    *,
    context: AgentToolContext,
    plan_index: int,
) -> Itinerary:
    if (
        plan_index < 0
        or plan_index
        >= len(context.plans)
    ):
        raise IndexError(
            "Plan index "
            f"{plan_index} is invalid. "
            f"Current candidate count: "
            f"{len(context.plans)}."
        )

    return context.plans[
        plan_index
    ]


def translate_search_category(
    category: str,
) -> str:
    translated = (
        AGENT_SEARCH_CATEGORY_MAP
        .get(
            category
        )
    )

    if translated is None:
        raise ValueError(
            "Unsupported PlanPilot "
            "search category: "
            f"{category}"
        )

    return translated


def live_place_to_venue(
    *,
    place: PlaceResult,
    category: str,
    request: PlanRequest,
) -> Venue:
    """
    Convert a live place result into the normalized Venue model.
    """

    cost_defaults = {
        "activity": 25.0,
        "restaurant": 28.0,
        "dessert": 12.0,
    }

    duration_defaults = {
        "activity": 75,
        "restaurant": 90,
        "dessert": 45,
    }

    if (
        category
        not in cost_defaults
    ):
        raise ValueError(
            "Unsupported PlanPilot "
            "venue category: "
            f"{category}"
        )

    area = (
        place.district
        or place.suburb
        or place.city
        or request.city
    )

    return Venue(
        name=place.name,
        category=category,
        area=area,
        estimated_cost_per_person=(
            cost_defaults[
                category
            ]
        ),
        duration_minutes=(
            duration_defaults[
                category
            ]
        ),
        vibe=list(
            request.vibe
        ),
        food_tags=[],
        latitude=place.latitude,
        longitude=place.longitude,
        formatted_address=(
            place.formatted_address
        ),
        website=place.website,
        opening_hours=(
            place.opening_hours
        ),
        source=place.source,
    )


def venue_identity(
    venue: Venue,
) -> tuple[
    str,
    str,
    float | None,
    float | None,
]:
    latitude = (
        round(
            venue.latitude,
            5,
        )
        if (
            venue.latitude
            is not None
        )
        else None
    )

    longitude = (
        round(
            venue.longitude,
            5,
        )
        if (
            venue.longitude
            is not None
        )
        else None
    )

    return (
        venue.name
        .strip()
        .lower(),
        venue.category,
        latitude,
        longitude,
    )


def merge_venues(
    *,
    existing: list[Venue],
    new_venues: list[Venue],
) -> list[Venue]:
    merged = list(
        existing
    )

    seen = {
        venue_identity(
            venue
        )
        for venue
        in existing
    }

    for venue in new_venues:
        identity = (
            venue_identity(
                venue
            )
        )

        if identity in seen:
            continue

        seen.add(
            identity
        )

        merged.append(
            venue
        )

    return merged


def summarize_validation(
    itinerary: Itinerary,
) -> str:
    if not (
        itinerary
        .validation_failures
    ):
        return (
            "Plan is valid and has no "
            "validation failures."
        )

    codes = [
        failure.code
        for failure
        in itinerary
        .validation_failures
    ]

    hard_error_count = sum(
        1
        for failure
        in itinerary
        .validation_failures
        if (
            failure.severity
            == "error"
        )
    )

    return (
        f"Plan has "
        f"{len(codes)} validation "
        f"issue(s), including "
        f"{hard_error_count} hard "
        f"error(s). Codes: "
        f"{', '.join(codes)}."
    )


def make_success_record(
    *,
    call: AgentToolCall,
    summary: str,
) -> ToolExecutionRecord:
    return ToolExecutionRecord(
        call_id=call.call_id,
        tool_name=call.tool_name,
        status="success",
        arguments=(
            call.arguments
        ),
        output_summary=summary,
        error_message=None,
    )


def make_error_record(
    *,
    call: AgentToolCall,
    message: str,
) -> ToolExecutionRecord:
    return ToolExecutionRecord(
        call_id=call.call_id,
        tool_name=call.tool_name,
        status="error",
        arguments=(
            call.arguments
        ),
        output_summary=None,
        error_message=message,
    )


# ---------------------------------------------------------------
# TOOL EXECUTORS
# ---------------------------------------------------------------


def execute_search_venues(
    *,
    call: AgentToolCall,
    context: AgentToolContext,
) -> tuple[
    ToolExecutionRecord,
    dict[str, Any],
]:
    """
    Search live venues and merge them into the working venue pool.

    When useful new venues are found, PlanPilot immediately rebuilds
    itinerary candidates so the LLM cannot forget to consume the new
    search results.
    """

    parsed = parse_tool_arguments(
        tool_name="search_venues",
        arguments=call.arguments,
    )

    provider_category = (
        translate_search_category(
            parsed.category
        )
    )

    try:
        places = search_places(
            query=parsed.query,
            city=parsed.city,
            category=(
                provider_category
            ),
            limit=parsed.limit,
        )

    except PlaceSearchError as exc:
        raise RuntimeError(
            str(exc)
        ) from exc

    new_venues = [
        live_place_to_venue(
            place=place,
            category=(
                parsed.category
            ),
            request=(
                context.request
            ),
        )
        for place
        in places
    ]

    previous_count = len(
        context.venue_source
    )

    context.venue_source = (
        merge_venues(
            existing=(
                context
                .venue_source
            ),
            new_venues=(
                new_venues
            ),
        )
    )

    added_count = (
        len(
            context.venue_source
        )
        - previous_count
    )

    plans_rebuilt = False

    if added_count > 0:
        context.plans = build_plans(
            request=(
                context.request
            ),
            venues=(
                context
                .venue_source
            ),
            start_coordinates=(
                context
                .start_coordinates
            ),
        )

        plans_rebuilt = True

    usable_plan_count = sum(
        1
        for plan
        in context.plans
        if not any(
            failure.severity
            == "error"
            for failure
            in plan
            .validation_failures
        )
    )

    payload = {
        "count": len(
            places
        ),
        "added_to_venue_pool": (
            added_count
        ),
        "venue_pool_size": len(
            context.venue_source
        ),
        "requested_category": (
            parsed.category
        ),
        "provider_category": (
            provider_category
        ),
        "plans_rebuilt": (
            plans_rebuilt
        ),
        "candidate_count": len(
            context.plans
        ),
        "usable_plan_count": (
            usable_plan_count
        ),
        "candidate_summaries": [
            {
                "index": index,
                "title": plan.title,
                "label": plan.label,
                "total_cost": (
                    plan.total_cost
                ),
                "score": (
                    plan.score
                ),
                "hard_error_count": sum(
                    1
                    for failure
                    in plan
                    .validation_failures
                    if (
                        failure.severity
                        == "error"
                    )
                ),
                "failure_codes": [
                    failure.code
                    for failure
                    in plan
                    .validation_failures
                ],
            }
            for index, plan
            in enumerate(
                context.plans
            )
        ],
        "places": [
            place.model_dump()
            for place
            in places
        ],
        "next_recommended_action": (
            (
                "Usable itinerary "
                "candidates now exist. "
                "Finish unless further "
                "validation is required."
            )
            if usable_plan_count > 0
            else (
                "New candidates were "
                "automatically rebuilt. "
                "Inspect or repair them "
                "instead of repeating "
                "venue searches."
            )
        ),
    }

    if added_count > 0:
        summary = (
            f"Found {len(places)} "
            f"venue result(s) for "
            f"'{parsed.query}' in "
            f"{parsed.city}. "
            f"Added {added_count} new "
            "venue(s) to the working "
            "venue pool. "
            f"Venue pool now contains "
            f"{len(context.venue_source)} "
            "venue(s). "
            "PlanPilot automatically "
            f"rebuilt {len(context.plans)} "
            "candidate(s). "
            f"{usable_plan_count} "
            "candidate(s) currently "
            "have no hard validation "
            "errors."
        )

    else:
        summary = (
            f"Found {len(places)} "
            f"venue result(s) for "
            f"'{parsed.query}' in "
            f"{parsed.city}, but all "
            "results were already "
            "present in the working "
            "venue pool. "
            f"Venue pool remains at "
            f"{len(context.venue_source)} "
            "venue(s). "
            "Do not repeat equivalent "
            "venue searches."
        )

    return (
        make_success_record(
            call=call,
            summary=summary,
        ),
        payload,
    )


def execute_build_plans(
    *,
    call: AgentToolCall,
    context: AgentToolContext,
) -> tuple[
    ToolExecutionRecord,
    dict[str, Any],
]:
    parsed = parse_tool_arguments(
        tool_name="build_plans",
        arguments=call.arguments,
    )

    context.request = (
        parsed.request
    )

    venue_source = (
        context.venue_source
        if context.venue_source
        else None
    )

    context.plans = build_plans(
        request=context.request,
        venues=venue_source,
        start_coordinates=(
            context
            .start_coordinates
        ),
    )

    payload = {
        "candidate_count": len(
            context.plans
        ),
        "venue_pool_size": len(
            context.venue_source
        ),
        "plans": [
            {
                "index": index,
                "title": plan.title,
                "label": plan.label,
                "total_cost": (
                    plan.total_cost
                ),
                "score": (
                    plan.score
                ),
                "validation_failures": [
                    failure.model_dump()
                    for failure
                    in plan
                    .validation_failures
                ],
            }
            for index, plan
            in enumerate(
                context.plans
            )
        ],
    }

    summary = (
        f"Generated "
        f"{len(context.plans)} "
        "itinerary candidate(s) "
        f"using a working venue pool "
        f"of {len(context.venue_source)} "
        "venue(s)."
    )

    return (
        make_success_record(
            call=call,
            summary=summary,
        ),
        payload,
    )


def execute_validate_plan(
    *,
    call: AgentToolCall,
    context: AgentToolContext,
) -> tuple[
    ToolExecutionRecord,
    dict[str, Any],
]:
    parsed = parse_tool_arguments(
        tool_name="validate_plan",
        arguments=call.arguments,
    )

    plan = get_plan_by_index(
        context=context,
        plan_index=(
            parsed.plan_index
        ),
    )

    validation_result = (
        validate_itinerary(
            request=context.request,
            itinerary=plan,
        )
    )

    plan.validation_failures = (
        validation_result
        .failures
    )

    plan.warnings = [
        failure.message
        for failure
        in validation_result
        .failures
    ]

    payload = {
        "plan_index": (
            parsed.plan_index
        ),
        "title": plan.title,
        "is_valid": (
            validation_result
            .is_valid
        ),
        "failures": [
            failure.model_dump()
            for failure
            in validation_result
            .failures
        ],
    }

    return (
        make_success_record(
            call=call,
            summary=(
                summarize_validation(
                    plan
                )
            ),
        ),
        payload,
    )


def execute_repair_plan(
    *,
    call: AgentToolCall,
    context: AgentToolContext,
) -> tuple[
    ToolExecutionRecord,
    dict[str, Any],
]:
    parsed = parse_tool_arguments(
        tool_name="repair_plan",
        arguments=call.arguments,
    )

    plan = get_plan_by_index(
        context=context,
        plan_index=(
            parsed.plan_index
        ),
    )

    venue_source = (
        context.venue_source
    )

    if not venue_source:
        raise RuntimeError(
            "Repair requires a venue "
            "source, but none is "
            "available in the agent "
            "context."
        )

    result = repair_itinerary(
        request=context.request,
        itinerary=plan,
        venues=venue_source,
        start_coordinates=(
            context
            .start_coordinates
        ),
        max_attempts=(
            parsed.max_attempts
        ),
        prefer_live=False,
    )

    if (
        result.final_itinerary
        is not None
    ):
        context.plans[
            parsed.plan_index
        ] = (
            result.final_itinerary
        )

    payload = {
        "plan_index": (
            parsed.plan_index
        ),
        "success": (
            result.success
        ),
        "exhausted": (
            result.exhausted
        ),
        "attempt_count": len(
            result.attempts
        ),
        "attempts": [
            attempt.model_dump()
            for attempt
            in result.attempts
        ],
        "final_plan": (
            result.final_itinerary
            .model_dump()
            if (
                result
                .final_itinerary
                is not None
            )
            else None
        ),
    }

    summary = (
        "Repair succeeded"
        if result.success
        else (
            "Repair did not fully "
            "succeed"
        )
    )

    summary += (
        f" after "
        f"{len(result.attempts)} "
        f"attempt(s)."
    )

    return (
        make_success_record(
            call=call,
            summary=summary,
        ),
        payload,
    )


# ---------------------------------------------------------------
# CENTRAL DISPATCHER
# ---------------------------------------------------------------


def execute_agent_tool(
    *,
    call: AgentToolCall,
    context: AgentToolContext,
) -> tuple[
    ToolExecutionRecord,
    dict[str, Any],
]:
    try:
        if (
            call.tool_name
            == "search_venues"
        ):
            return (
                execute_search_venues(
                    call=call,
                    context=context,
                )
            )

        if (
            call.tool_name
            == "build_plans"
        ):
            return (
                execute_build_plans(
                    call=call,
                    context=context,
                )
            )

        if (
            call.tool_name
            == "validate_plan"
        ):
            return (
                execute_validate_plan(
                    call=call,
                    context=context,
                )
            )

        if (
            call.tool_name
            == "repair_plan"
        ):
            return (
                execute_repair_plan(
                    call=call,
                    context=context,
                )
            )

        raise ValueError(
            "Unsupported agent tool: "
            f"{call.tool_name}"
        )

    except (
        ValidationError,
        ValueError,
        IndexError,
        RuntimeError,
    ) as exc:
        record = (
            make_error_record(
                call=call,
                message=str(exc),
            )
        )

        return (
            record,
            {
                "error": str(
                    exc
                ),
            },
        )


def tool_names() -> list[
    AgentToolName
]:
    return [
        "search_venues",
        "build_plans",
        "validate_plan",
        "repair_plan",
    ]
