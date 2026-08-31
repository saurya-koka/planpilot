from backend.app.agent_models import (
    AgentToolCall,
)
from backend.app.agent_tools import (
    AgentToolContext,
    execute_agent_tool,
    live_place_to_venue,
    merge_venues,
    tool_names,
    translate_search_category,
)
from backend.app.models import (
    PlaceResult,
    PlanRequest,
    Venue,
)


def make_request(
    *,
    budget_total: float = 200,
) -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=budget_total,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=30,
    )


def make_venues() -> list[Venue]:
    return [
        Venue(
            name="Expensive Restaurant",
            category="restaurant",
            area="Back Bay",
            estimated_cost_per_person=60,
            duration_minutes=60,
            vibe=[
                "chill",
            ],
            opening_hours=(
                "Mo-Su 16:00-23:00"
            ),
            source="sample",
        ),
        Venue(
            name="Affordable Restaurant",
            category="restaurant",
            area="Back Bay",
            estimated_cost_per_person=30,
            duration_minutes=60,
            vibe=[
                "chill",
            ],
            opening_hours=(
                "Mo-Su 16:00-23:00"
            ),
            source="sample",
        ),
    ]


def test_tool_names_are_exposed() -> None:
    assert tool_names() == [
        "search_venues",
        "build_plans",
        "validate_plan",
        "repair_plan",
    ]


def test_build_plans_tool_executes() -> None:
    request = make_request()

    context = AgentToolContext(
        request=request,
        venue_source=make_venues(),
    )

    call = AgentToolCall(
        call_id="call-build-1",
        tool_name="build_plans",
        arguments={
            "request": (
                request.model_dump()
            ),
        },
        rationale=(
            "Generate itinerary "
            "candidates."
        ),
    )

    record, payload = (
        execute_agent_tool(
            call=call,
            context=context,
        )
    )

    assert (
        record.status
        == "success"
    )

    assert (
        record.tool_name
        == "build_plans"
    )

    assert (
        payload[
            "candidate_count"
        ]
        >= 1
    )

    assert context.plans


def test_validate_plan_tool_executes() -> None:
    request = make_request()

    context = AgentToolContext(
        request=request,
        venue_source=make_venues(),
    )

    build_call = AgentToolCall(
        call_id="call-build-2",
        tool_name="build_plans",
        arguments={
            "request": (
                request.model_dump()
            ),
        },
        rationale="Build plans.",
    )

    execute_agent_tool(
        call=build_call,
        context=context,
    )

    validate_call = AgentToolCall(
        call_id="call-validate-1",
        tool_name="validate_plan",
        arguments={
            "plan_index": 0,
        },
        rationale=(
            "Validate the first "
            "candidate."
        ),
    )

    record, payload = (
        execute_agent_tool(
            call=validate_call,
            context=context,
        )
    )

    assert (
        record.status
        == "success"
    )

    assert (
        payload[
            "plan_index"
        ]
        == 0
    )

    assert (
        "is_valid"
        in payload
    )

    assert (
        "failures"
        in payload
    )


def test_repair_plan_tool_repairs_budget_failure() -> None:
    request = make_request(
        budget_total=80,
    )

    venues = make_venues()

    context = AgentToolContext(
        request=request,
        venue_source=venues,
    )

    from backend.app.planner import (
        build_itinerary,
    )

    broken_plan = build_itinerary(
        request=request,
        chosen_venues=[
            venues[0],
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    context.plans = [
        broken_plan,
    ]

    assert any(
        failure.code
        == "budget_exceeded"
        for failure
        in broken_plan
        .validation_failures
    )

    call = AgentToolCall(
        call_id="call-repair-1",
        tool_name="repair_plan",
        arguments={
            "plan_index": 0,
            "max_attempts": 3,
        },
        rationale=(
            "Repair the budget "
            "violation."
        ),
    )

    record, payload = (
        execute_agent_tool(
            call=call,
            context=context,
        )
    )

    assert (
        record.status
        == "success"
    )

    assert (
        payload[
            "success"
        ]
        is True
    )

    assert (
        context.plans[0]
        .title
        == "Affordable Restaurant"
    )

    assert not any(
        failure.severity
        == "error"
        for failure
        in context.plans[0]
        .validation_failures
    )


def test_invalid_plan_index_returns_tool_error() -> None:
    request = make_request()

    context = AgentToolContext(
        request=request,
        venue_source=make_venues(),
    )

    call = AgentToolCall(
        call_id="call-invalid-index",
        tool_name="validate_plan",
        arguments={
            "plan_index": 99,
        },
        rationale=(
            "Try validating an "
            "invalid index."
        ),
    )

    record, payload = (
        execute_agent_tool(
            call=call,
            context=context,
        )
    )

    assert (
        record.status
        == "error"
    )

    assert (
        "error"
        in payload
    )

    assert (
        "invalid"
        in payload[
            "error"
        ].lower()
    )


def test_invalid_tool_arguments_return_error() -> None:
    request = make_request()

    context = AgentToolContext(
        request=request,
        venue_source=make_venues(),
    )

    call = AgentToolCall(
        call_id="call-invalid-args",
        tool_name="repair_plan",
        arguments={
            "plan_index": 0,
            "max_attempts": 99,
        },
        rationale=(
            "Use invalid repair "
            "arguments."
        ),
    )

    record, payload = (
        execute_agent_tool(
            call=call,
            context=context,
        )
    )

    assert (
        record.status
        == "error"
    )

    assert (
        "error"
        in payload
    )


def test_build_plans_tool_updates_context_request() -> None:
    original_request = (
        make_request(
            budget_total=200,
        )
    )

    updated_request = (
        make_request(
            budget_total=120,
        )
    )

    context = AgentToolContext(
        request=original_request,
        venue_source=make_venues(),
    )

    call = AgentToolCall(
        call_id="call-context-update",
        tool_name="build_plans",
        arguments={
            "request": (
                updated_request
                .model_dump()
            ),
        },
        rationale=(
            "Rebuild using updated "
            "constraints."
        ),
    )

    record, _ = (
        execute_agent_tool(
            call=call,
            context=context,
        )
    )

    assert (
        record.status
        == "success"
    )

    assert (
        context.request
        .budget_total
        == 120
    )


def test_restaurant_category_translates_for_geoapify() -> None:
    assert (
        translate_search_category(
            "restaurant"
        )
        == "catering.restaurant"
    )


def test_activity_category_translates_for_geoapify() -> None:
    assert (
        translate_search_category(
            "activity"
        )
        == "entertainment"
    )


def test_dessert_category_translates_for_geoapify() -> None:
    assert (
        translate_search_category(
            "dessert"
        )
        == "catering"
    )


def test_merge_venues_adds_new_unique_venue() -> None:
    request = make_request()

    context = (
        AgentToolContext(
            request=request,
            venue_source=[],
        )
    )

    place = PlaceResult(
        place_id="live-1",
        name="Test Bistro",
        formatted_address=(
            "123 Newbury St, Boston, MA"
        ),
        latitude=42.3501,
        longitude=-71.0810,
        categories=[
            "catering.restaurant",
        ],
        city="Boston",
        district="Back Bay",
        source="geoapify",
    )

    venue = (
        live_place_to_venue(
            place=place,
            category="restaurant",
            request=request,
        )
    )

    context.venue_source = (
        merge_venues(
            existing=(
                context
                .venue_source
            ),
            new_venues=[
                venue,
            ],
        )
    )

    assert (
        len(
            context
            .venue_source
        )
        == 1
    )

    assert (
        context
        .venue_source[0]
        .name
        == "Test Bistro"
    )

    assert (
        context
        .venue_source[0]
        .category
        == "restaurant"
    )


def test_merge_venues_deduplicates_same_live_venue() -> None:
    request = make_request()

    place = PlaceResult(
        place_id="live-1",
        name="Test Bistro",
        formatted_address=(
            "123 Newbury St, Boston, MA"
        ),
        latitude=42.3501,
        longitude=-71.0810,
        categories=[
            "catering.restaurant",
        ],
        city="Boston",
        district="Back Bay",
        source="geoapify",
    )

    venue = (
        live_place_to_venue(
            place=place,
            category="restaurant",
            request=request,
        )
    )

    merged = merge_venues(
        existing=[
            venue,
        ],
        new_venues=[
            venue,
        ],
    )

    assert (
        len(
            merged
        )
        == 1
    )


def test_search_with_new_venues_rebuilds_plans(
    monkeypatch,
) -> None:
    request = make_request()

    context = AgentToolContext(
        request=request,
        venue_source=make_venues(),
    )

    live_place = PlaceResult(
        place_id="live-search-1",
        name="New Back Bay Bistro",
        formatted_address=(
            "100 Newbury St, Boston, MA"
        ),
        latitude=42.3505,
        longitude=-71.0785,
        categories=[
            "catering.restaurant",
        ],
        city="Boston",
        district="Back Bay",
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="geoapify",
    )

    def fake_search_places(
        *,
        query,
        city,
        category,
        limit,
    ):
        return [
            live_place,
        ]

    monkeypatch.setattr(
        "backend.app.agent_tools.search_places",
        fake_search_places,
    )

    call = AgentToolCall(
        call_id="call-live-search",
        tool_name="search_venues",
        arguments={
            "query": (
                "casual dinner "
                "near Back Bay"
            ),
            "city": "Boston",
            "category": "restaurant",
            "limit": 10,
        },
        rationale=(
            "Find another nearby "
            "restaurant."
        ),
    )

    record, payload = (
        execute_agent_tool(
            call=call,
            context=context,
        )
    )

    assert (
        record.status
        == "success"
    )

    assert (
        payload[
            "added_to_venue_pool"
        ]
        == 1
    )

    assert (
        payload[
            "plans_rebuilt"
        ]
        is True
    )

    assert (
        payload[
            "candidate_count"
        ]
        >= 1
    )

    assert (
        len(
            context.plans
        )
        >= 1
    )

    assert any(
        venue.name
        == "New Back Bay Bistro"
        for venue
        in context.venue_source
    )
