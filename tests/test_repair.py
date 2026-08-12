from backend.app.models import (
    PlanRequest,
    Venue,
)
from backend.app.planner import (
    build_itinerary,
)
from backend.app.repair import (
    choose_repair_actions,
    repair_itinerary,
)


def make_request(
    *,
    budget_total: float = 200,
    max_leg_minutes: int = 30,
) -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=budget_total,
        party_size=2,
        transport="walking",
        vibe=["chill"],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=max_leg_minutes,
    )


def test_budget_repair_replaces_expensive_venue() -> None:
    request = make_request(
        budget_total=80,
    )

    expensive = Venue(
        name="Expensive Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=60,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    affordable = Venue(
        name="Affordable Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    venues = [
        expensive,
        affordable,
    ]

    itinerary = build_itinerary(
        request=request,
        chosen_venues=[
            expensive,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    assert any(
        failure.code
        == "budget_exceeded"
        for failure
        in itinerary.validation_failures
    )

    result = repair_itinerary(
        request=request,
        itinerary=itinerary,
        venues=venues,
        start_coordinates=None,
        prefer_live=False,
    )

    assert result.success is True

    assert (
        result.final_itinerary
        is not None
    )

    assert (
        result.final_itinerary
        .title
        == "Affordable Restaurant"
    )

    assert (
        result.final_itinerary
        .total_cost
        == 60
    )

    assert not any(
        failure.severity
        == "error"
        for failure
        in result.final_itinerary
        .validation_failures
    )

    assert len(
        result.attempts
    ) == 1

    action = (
        result.attempts[0]
        .actions[0]
    )

    assert (
        action.strategy
        == "replace_expensive_venue"
    )

    assert (
        action.target_name
        == "Expensive Restaurant"
    )

    assert (
        action.replacement_name
        == "Affordable Restaurant"
    )


def test_closed_venue_repair_uses_open_alternative() -> None:
    request = make_request(
        budget_total=200,
    )

    closed = Venue(
        name="Lunch Only Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=25,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Fr 07:00-15:00",
        source="sample",
    )

    open_venue = Venue(
        name="Evening Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Fr 16:00-23:00",
        source="sample",
    )

    venues = [
        closed,
        open_venue,
    ]

    itinerary = build_itinerary(
        request=request,
        chosen_venues=[
            closed,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    assert any(
        failure.code
        == "venue_closed"
        for failure
        in itinerary.validation_failures
    )

    result = repair_itinerary(
        request=request,
        itinerary=itinerary,
        venues=venues,
        start_coordinates=None,
        prefer_live=False,
    )

    assert result.success is True

    assert (
        result.final_itinerary
        is not None
    )

    assert (
        result.final_itinerary
        .title
        == "Evening Restaurant"
    )

    assert not any(
        failure.code
        == "venue_closed"
        for failure
        in result.final_itinerary
        .validation_failures
    )


def test_long_travel_repair_replaces_distant_venue() -> None:
    request = make_request(
        budget_total=300,
        max_leg_minutes=20,
    )

    nearby_activity = Venue(
        name="Nearby Activity",
        category="activity",
        area="Back Bay",
        estimated_cost_per_person=10,
        duration_minutes=60,
        vibe=["chill"],
        latitude=42.3500,
        longitude=-71.0800,
        opening_hours="Mo-Su 09:00-23:00",
        source="sample",
    )

    distant_restaurant = Venue(
        name="Distant Restaurant",
        category="restaurant",
        area="Far Area",
        estimated_cost_per_person=30,
        duration_minutes=60,
        vibe=["chill"],
        latitude=42.5000,
        longitude=-71.3000,
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    nearby_restaurant = Venue(
        name="Nearby Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=35,
        duration_minutes=60,
        vibe=["chill"],
        latitude=42.3510,
        longitude=-71.0810,
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    venues = [
        nearby_activity,
        distant_restaurant,
        nearby_restaurant,
    ]

    itinerary = build_itinerary(
        request=request,
        chosen_venues=[
            nearby_activity,
            distant_restaurant,
        ],
        start_coordinates=(
            42.3495,
            -71.0810,
        ),
        prefer_live=False,
    )

    assert any(
        failure.code
        == "travel_leg_too_long"
        for failure
        in itinerary.validation_failures
    )

    result = repair_itinerary(
        request=request,
        itinerary=itinerary,
        venues=venues,
        start_coordinates=(
            42.3495,
            -71.0810,
        ),
        prefer_live=False,
    )

    assert result.success is True

    assert (
        result.final_itinerary
        is not None
    )

    assert (
        "Nearby Restaurant"
        in result.final_itinerary.title
    )

    assert not any(
        failure.code
        == "travel_leg_too_long"
        for failure
        in result.final_itinerary
        .validation_failures
    )


def test_repair_trace_records_attempt() -> None:
    request = make_request(
        budget_total=80,
    )

    expensive = Venue(
        name="Expensive Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=60,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    affordable = Venue(
        name="Affordable Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    venues = [
        expensive,
        affordable,
    ]

    itinerary = build_itinerary(
        request=request,
        chosen_venues=[
            expensive,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    result = repair_itinerary(
        request=request,
        itinerary=itinerary,
        venues=venues,
        start_coordinates=None,
        prefer_live=False,
    )

    assert len(
        result.attempts
    ) == 1

    attempt = (
        result.attempts[0]
    )

    assert (
        attempt.attempt_number
        == 1
    )

    assert (
        "budget_exceeded"
        in attempt.failure_codes
    )

    assert (
        attempt.success
        is True
    )

    assert (
        attempt.output_plan_title
        == "Affordable Restaurant"
    )


def test_no_repair_needed_returns_success_without_attempts() -> None:
    request = make_request(
        budget_total=200,
    )

    venue = Venue(
        name="Valid Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    itinerary = build_itinerary(
        request=request,
        chosen_venues=[
            venue,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    result = repair_itinerary(
        request=request,
        itinerary=itinerary,
        venues=[
            venue,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    assert result.success is True

    assert (
        result.attempts
        == []
    )

    assert (
        result.final_itinerary
        is not None
    )

    assert (
        result.final_itinerary
        .title
        == "Valid Restaurant"
    )


def test_repair_fails_gracefully_when_no_replacement_exists() -> None:
    request = make_request(
        budget_total=50,
    )

    expensive = Venue(
        name="Only Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=60,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours="Mo-Su 16:00-23:00",
        source="sample",
    )

    itinerary = build_itinerary(
        request=request,
        chosen_venues=[
            expensive,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    actions = choose_repair_actions(
        itinerary=itinerary,
        venues=[
            expensive,
        ],
    )

    assert actions

    assert (
        actions[0].strategy
        == "no_action"
    )

    result = repair_itinerary(
        request=request,
        itinerary=itinerary,
        venues=[
            expensive,
        ],
        start_coordinates=None,
        prefer_live=False,
    )

    assert result.success is False

    assert (
        result.exhausted
        is False
    )

    assert len(
        result.attempts
    ) == 1
