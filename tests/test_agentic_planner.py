from backend.app.models import (
    PlanRequest,
    Venue,
)
from backend.app.planner import (
    build_itinerary,
    build_plans,
    repair_plan_if_needed,
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


def test_build_plans_repairs_budget_violation_automatically() -> None:
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

    plans = build_plans(
        request=request,
        venues=[
            expensive,
            affordable,
        ],
    )

    assert plans

    assert all(
        plan.total_cost
        <= request.budget_total
        for plan in plans
    )

    assert any(
        "Affordable Restaurant"
        in plan.title
        for plan in plans
    )

    assert all(
        not any(
            failure.severity
            == "error"
            for failure
            in plan.validation_failures
        )
        for plan in plans
    )


def test_build_plans_repairs_closed_venue_automatically() -> None:
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

    plans = build_plans(
        request=request,
        venues=[
            closed,
            open_venue,
        ],
    )

    assert plans

    assert all(
        "Lunch Only Restaurant"
        not in plan.title
        for plan in plans
    )

    assert any(
        "Evening Restaurant"
        in plan.title
        for plan in plans
    )

    assert all(
        not any(
            failure.code
            == "venue_closed"
            for failure
            in plan.validation_failures
        )
        for plan in plans
    )


def test_build_plans_repairs_long_travel_automatically() -> None:
    request = PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=300,
        party_size=2,
        transport="walking",
        vibe=["chill"],
        must_include=[
            "activity",
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=20,
    )

    activity = Venue(
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

    plans = build_plans(
        request=request,
        venues=[
            activity,
            distant_restaurant,
            nearby_restaurant,
        ],
        start_coordinates=(
            42.3495,
            -71.0810,
        ),
    )

    assert plans

    assert any(
        "Nearby Restaurant"
        in plan.title
        for plan in plans
    )

    assert all(
        not any(
            failure.code
            == "travel_leg_too_long"
            for failure
            in plan.validation_failures
        )
        for plan in plans
    )


def test_planner_repair_stage_records_agentic_reason() -> None:
    """
    Verify that the planner's repair stage records provenance.

    build_plans() may later deduplicate a repaired itinerary against
    an identical candidate that was already valid, so provenance is
    tested before that intentional deduplication step.
    """
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

    broken_plan = build_itinerary(
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
        in broken_plan.validation_failures
    )

    repaired_plan = repair_plan_if_needed(
        plan=broken_plan,
        request=request,
        venue_source=venues,
        start_coordinates=None,
        prefer_live=False,
    )

    assert (
        repaired_plan.title
        == "Affordable Restaurant"
    )

    assert any(
        reason.startswith(
            "Agentic repair adjusted"
        )
        for reason
        in repaired_plan.reasons
    )

    assert not any(
        failure.severity
        == "error"
        for failure
        in repaired_plan.validation_failures
    )
