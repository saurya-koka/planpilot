from __future__ import annotations

from .agent_controller import (
    has_usable_plan,
)
from .agent_tools import (
    live_place_to_venue,
    merge_venues,
    translate_search_category,
)
from .graph_state import (
    PlanPilotGraphState,
)
from .models import (
    PlanRequest,
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


def initialize_graph_state(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Normalize graph counters and flags at the start of execution.
    """

    return {
        "selected_plan_index": (
            state.get(
                "selected_plan_index",
                0,
            )
        ),
        "has_usable_plan": False,
        "iteration_count": (
            state.get(
                "iteration_count",
                0,
            )
        ),
        "max_iterations": (
            state.get(
                "max_iterations",
                4,
            )
        ),
        "searched_categories": list(
            state.get(
                "searched_categories",
                [],
            )
        ),
        "search_count": (
            state.get(
                "search_count",
                0,
            )
        ),
        "last_action": (
            "Graph initialized."
        ),
        "final_message": "",
        "exhausted": False,
    }


def build_plans_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Generate itinerary candidates from the current venue pool.
    """

    request = state[
        "request"
    ]

    venues = state.get(
        "venues",
        [],
    )

    plans = build_plans(
        request=request,
        venues=(
            venues
            if venues
            else None
        ),
        start_coordinates=(
            state.get(
                "start_coordinates"
            )
        ),
    )

    return {
        "plans": plans,
        "selected_plan_index": 0,
        "has_usable_plan": (
            has_usable_plan(
                plans
            )
        ),
        "last_action": (
            f"Built {len(plans)} "
            "itinerary candidate(s)."
        ),
    }


def validate_plans_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Inspect validation failures already attached to the plans.
    """

    plans = state.get(
        "plans",
        [],
    )

    usable = (
        has_usable_plan(
            plans
        )
    )

    selected_index = 0

    if plans:
        for index, plan in enumerate(
            plans
        ):
            hard_errors = any(
                failure.severity
                == "error"
                for failure
                in plan.validation_failures
            )

            if not hard_errors:
                selected_index = index
                break

    return {
        "selected_plan_index": (
            selected_index
        ),
        "has_usable_plan": usable,
        "last_action": (
            (
                "Validation found at least "
                "one usable itinerary."
            )
            if usable
            else (
                "Validation found no "
                "usable itinerary."
            )
        ),
    }


def repair_selected_plan_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Attempt deterministic repair of the selected candidate.
    """

    plans = list(
        state.get(
            "plans",
            [],
        )
    )

    venues = state.get(
        "venues",
        [],
    )

    request = state[
        "request"
    ]

    if not plans:
        return {
            "last_action": (
                "Repair skipped because "
                "no plans exist."
            ),
        }

    if not venues:
        return {
            "last_action": (
                "Repair skipped because "
                "no venue pool exists."
            ),
        }

    selected_index = state.get(
        "selected_plan_index",
        0,
    )

    if (
        selected_index < 0
        or selected_index >= len(plans)
    ):
        selected_index = 0

    selected_plan = plans[
        selected_index
    ]

    result = repair_itinerary(
        request=request,
        itinerary=selected_plan,
        venues=venues,
        start_coordinates=(
            state.get(
                "start_coordinates"
            )
        ),
        max_attempts=3,
        prefer_live=False,
    )

    if (
        result.final_itinerary
        is not None
    ):
        plans[
            selected_index
        ] = (
            result.final_itinerary
        )

    next_iteration = (
        state.get(
            "iteration_count",
            0,
        )
        + 1
    )

    return {
        "plans": plans,
        "iteration_count": (
            next_iteration
        ),
        "has_usable_plan": (
            has_usable_plan(
                plans
            )
        ),
        "last_action": (
            (
                "Repair produced a "
                "usable itinerary."
            )
            if result.success
            else (
                "Repair completed but "
                "hard errors remain."
            )
        ),
    }


def required_search_categories(
    request: PlanRequest,
) -> list[str]:
    """
    Translate itinerary requirements into PlanPilot venue categories.

    This gives the graph a deterministic way to decide what kind of
    venue should be searched for when repair cannot solve the current
    candidate set.
    """

    categories: list[
        str
    ] = []

    requirements = {
        item.strip().lower()
        for item
        in request.must_include
    }

    if any(
        value
        in requirements
        for value
        in {
            "activity",
            "activities",
            "entertainment",
        }
    ):
        categories.append(
            "activity"
        )

    if any(
        value
        in requirements
        for value
        in {
            "dinner",
            "restaurant",
            "food",
            "meal",
        }
    ):
        categories.append(
            "restaurant"
        )

    if any(
        value
        in requirements
        for value
        in {
            "dessert",
            "desserts",
            "sweets",
        }
    ):
        categories.append(
            "dessert"
        )

    if not categories:
        categories.append(
            "restaurant"
        )

    return categories


def build_search_query(
    *,
    request: PlanRequest,
    category: str,
) -> str:
    """
    Build a compact search query from the structured request.
    """

    parts: list[
        str
    ] = []

    parts.extend(
        request.vibe[:2]
    )

    if (
        category
        == "restaurant"
    ):
        parts.extend(
            request.food_preferences[:2]
        )

        parts.append(
            "restaurant"
        )

    elif (
        category
        == "activity"
    ):
        parts.append(
            "activity"
        )

    else:
        parts.append(
            "dessert"
        )

    cleaned = [
        part.strip()
        for part
        in parts
        if part.strip()
    ]

    return " ".join(
        cleaned
    )


def search_venues_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Search for one previously unsearched venue category.

    New live venues are normalized using the same helpers as the V2.5
    OpenAI tool-calling agent, merged into the working venue pool, and
    immediately consumed by the planner.
    """

    request = state[
        "request"
    ]

    existing_venues = list(
        state.get(
            "venues",
            [],
        )
    )

    searched_categories = list(
        state.get(
            "searched_categories",
            [],
        )
    )

    required_categories = (
        required_search_categories(
            request
        )
    )

    category = next(
        (
            candidate
            for candidate
            in required_categories
            if candidate
            not in searched_categories
        ),
        None,
    )

    if category is None:
        return {
            "last_action": (
                "Search skipped because "
                "all required venue "
                "categories were already "
                "searched."
            ),
        }

    query = build_search_query(
        request=request,
        category=category,
    )

    provider_category = (
        translate_search_category(
            category
        )
    )

    next_searched_categories = (
        searched_categories
        + [
            category,
        ]
    )

    next_search_count = (
        state.get(
            "search_count",
            0,
        )
        + 1
    )

    try:
        places = search_places(
            query=query,
            city=request.city,
            category=(
                provider_category
            ),
            limit=10,
        )

    except PlaceSearchError as exc:
        return {
            "searched_categories": (
                next_searched_categories
            ),
            "search_count": (
                next_search_count
            ),
            "last_action": (
                "Live venue search failed "
                f"for {category}: {exc}"
            ),
        }

    new_venues = [
        live_place_to_venue(
            place=place,
            category=category,
            request=request,
        )
        for place
        in places
    ]

    merged_venues = (
        merge_venues(
            existing=(
                existing_venues
            ),
            new_venues=(
                new_venues
            ),
        )
    )

    added_count = (
        len(merged_venues)
        - len(existing_venues)
    )

    plans = list(
        state.get(
            "plans",
            [],
        )
    )

    if added_count > 0:
        plans = build_plans(
            request=request,
            venues=merged_venues,
            start_coordinates=(
                state.get(
                    "start_coordinates"
                )
            ),
        )

    return {
        "venues": (
            merged_venues
        ),
        "plans": plans,
        "searched_categories": (
            next_searched_categories
        ),
        "search_count": (
            next_search_count
        ),
        "has_usable_plan": (
            has_usable_plan(
                plans
            )
        ),
        "selected_plan_index": 0,
        "last_action": (
            f"Searched {category} venues. "
            f"Found {len(places)} result(s), "
            f"added {added_count} new venue(s), "
            f"and now have {len(plans)} "
            "candidate plan(s)."
        ),
    }


def finish_graph_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Finalize graph execution.
    """

    usable = (
        has_usable_plan(
            state.get(
                "plans",
                [],
            )
        )
    )

    exhausted = (
        (
            not usable
        )
        and (
            state.get(
                "iteration_count",
                0,
            )
            >= state.get(
                "max_iterations",
                4,
            )
        )
    )

    return {
        "has_usable_plan": usable,
        "exhausted": exhausted,
        "final_message": (
            (
                "LangGraph orchestration "
                "completed with at least "
                "one usable itinerary."
            )
            if usable
            else (
                "LangGraph orchestration "
                "finished without a usable "
                "itinerary."
            )
        ),
        "last_action": (
            "Graph finished."
        ),
    }
