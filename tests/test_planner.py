from backend.app.models import PlanRequest
from backend.app.planner import build_plans


def test_returns_three_ranked_plans() -> None:
    """
    The first returned plan must be the best overall plan.

    The remaining plans may be selected for lower cost or stronger
    vibe matching, so they are not required to be sorted by score.
    """
    plans = build_plans(PlanRequest())

    assert len(plans) == 3
    assert plans[0].label == "Best overall"

    highest_returned_score = max(
        plan.score
        for plan in plans
    )

    assert plans[0].score == highest_returned_score


def test_valid_plans_respect_budget_and_leg_limit() -> None:
    request = PlanRequest(
        city="Boston",
        start_area="Davis Square",
        budget_total=250,
        party_size=2,
        vibe=["romantic", "fun"],
        must_include=[
            "activity",
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=60,
    )

    plans = build_plans(request)

    assert len(plans) == 3

    for plan in plans:
        assert plan.total_cost <= request.budget_total
        assert plan.warnings == []


def test_returns_distinct_plan_labels() -> None:
    request = PlanRequest(
        city="Boston",
        start_area="Davis Square",
        budget_total=250,
        party_size=2,
        vibe=["romantic", "fun"],
        must_include=[
            "activity",
            "dinner",
            "dessert",
        ],
        food_preferences=[],
        max_leg_minutes=60,
    )

    plans = build_plans(request)

    labels = [
        plan.label
        for plan in plans
    ]

    assert len(plans) == 3
    assert labels[0] == "Best overall"
    assert "Lowest cost" in labels
    assert "Best vibe match" in labels


def test_returned_plans_are_unique() -> None:
    request = PlanRequest(
        city="Boston",
        start_area="Davis Square",
        budget_total=250,
        party_size=2,
        vibe=["romantic"],
        must_include=[
            "activity",
            "dinner",
            "dessert",
        ],
        food_preferences=[],
        max_leg_minutes=60,
    )

    plans = build_plans(request)

    titles = [
        plan.title
        for plan in plans
    ]

    assert len(plans) == 3
    assert len(titles) == len(set(titles))


def test_lowest_cost_plan_is_cheapest_distinct_option() -> None:
    request = PlanRequest(
        city="Boston",
        start_area="Davis Square",
        budget_total=300,
        party_size=2,
        vibe=["romantic", "fun"],
        must_include=[
            "activity",
            "dinner",
            "dessert",
        ],
        food_preferences=[],
        max_leg_minutes=60,
    )

    plans = build_plans(request)

    lowest_cost_plan = next(
        plan
        for plan in plans
        if plan.label == "Lowest cost"
    )

    assert lowest_cost_plan.total_cost <= max(
        plan.total_cost
        for plan in plans
    )


def test_requested_categories_appear_in_plan() -> None:
    request = PlanRequest(
        city="Boston",
        start_area="Davis Square",
        budget_total=300,
        party_size=2,
        vibe=["romantic"],
        must_include=[
            "dinner",
            "dessert",
        ],
        food_preferences=[],
        max_leg_minutes=60,
    )

    plans = build_plans(request)

    assert len(plans) > 0

    for plan in plans:
        categories = [
            stop.category
            for stop in plan.stops
        ]

        assert categories == [
            "restaurant",
            "dessert",
        ]
