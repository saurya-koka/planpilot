from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ok"
    assert "llm_configured" in body


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert body["name"] == "PlanPilot API"
    assert body["status"] == "running"
    assert body["docs"] == "/docs"


def test_manual_plan_generation() -> None:
    payload = {
        "city": "Boston",
        "start_area": "Davis Square",
        "date": "Friday",
        "start_time": "18:00",
        "budget_total": 200,
        "party_size": 2,
        "transport": "public_transit",
        "vibe": ["romantic"],
        "must_include": [
            "activity",
            "dinner",
        ],
        "food_preferences": [],
        "max_leg_minutes": 30,
    }

    response = client.post(
        "/plans",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["request"]["city"] == "Boston"
    assert len(body["plans"]) > 0
    assert len(body["plans"]) <= 3

    for plan in body["plans"]:
        assert plan["total_cost"] >= 0
        assert len(plan["stops"]) == 2
        assert plan["stops"][0]["category"] == "activity"
        assert plan["stops"][1]["category"] == "restaurant"


def test_plan_from_text_generates_options() -> None:
    payload = {
        "text": (
            "Plan a romantic date in Boston this Friday "
            "after 6 PM for two people under $180. "
            "Include dinner and dessert. We have no car."
        ),
        "start_area": "Davis Square",
        "food_preferences": [],
    }

    response = client.post(
        "/plan-from-text",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["original_text"] == payload["text"]
    assert body["parsed_request"]["city"] == "Boston"
    assert body["parsed_request"]["party_size"] == 2
    assert body["parsed_request"]["include_dinner"] is True
    assert body["parsed_request"]["include_dessert"] is True

    assert len(body["plans"]) > 0
    assert len(body["plans"]) <= 3

    for plan in body["plans"]:
        categories = [
            stop["category"]
            for stop in plan["stops"]
        ]

        assert "restaurant" in categories
        assert "dessert" in categories


def test_plan_from_text_respects_budget_field() -> None:
    payload = {
        "text": (
            "Plan a fun outing in Boston for two people "
            "under $150 with an activity and dinner."
        ),
        "start_area": "Davis Square",
        "food_preferences": [],
    }

    response = client.post(
        "/plan-from-text",
        json=payload,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["parsed_request"]["budget"] == 150
    assert body["planning_request"]["budget_total"] == 150


def test_invalid_manual_request_is_rejected() -> None:
    payload = {
        "city": "Boston",
        "budget_total": -50,
        "party_size": 0,
    }

    response = client.post(
        "/plans",
        json=payload,
    )

    assert response.status_code == 422
