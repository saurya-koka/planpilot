from backend.app.models import PlanRequest
from backend.app.planner import build_plans


def test_returns_three_ranked_plans():
    plans = build_plans(PlanRequest())
    assert len(plans) == 3
    assert plans[0].score >= plans[1].score >= plans[2].score


def test_valid_plans_respect_budget_and_leg_limit():
    request = PlanRequest(budget_total=250, max_leg_minutes=40)
    plans = build_plans(request)
    assert all(plan.total_cost <= request.budget_total for plan in plans)
    assert all(not plan.warnings for plan in plans)
