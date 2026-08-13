from __future__ import annotations

from backend.app.models import (
    PlanRequest,
)
from backend.app.reranker import (
    area_match_score,
    budget_fit_score,
    food_match_score,
    proximity_score,
    rerank_results,
    score_retrieval_result,
    semantic_score_from_distance,
)
from backend.app.vector_store import (
    RetrievalResult,
)


def make_request() -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="18:00",
        budget_total=120,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
            "foodie",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[
            "chicken",
        ],
        max_leg_minutes=45,
    )


def make_result(
    *,
    document_id: str,
    name: str,
    area: str,
    food_tags: str,
    vibe: str,
    cost: float,
    latitude: float,
    longitude: float,
    distance: float,
    category: str = "restaurant",
) -> RetrievalResult:
    return RetrievalResult(
        document_id=document_id,
        text=(
            f"{name} is a "
            f"{category} in {area}."
        ),
        metadata={
            "name": name,
            "category": category,
            "area": area,
            "food_tags": food_tags,
            "vibe": vibe,
            "estimated_cost_per_person": (
                cost
            ),
            "latitude": latitude,
            "longitude": longitude,
        },
        distance=distance,
    )


def test_semantic_score_prefers_smaller_distance() -> None:
    close = (
        semantic_score_from_distance(
            0.2
        )
    )

    far = (
        semantic_score_from_distance(
            1.0
        )
    )

    assert close > far


def test_food_match_recognizes_partial_tag() -> None:
    request = make_request()

    score = food_match_score(
        metadata={
            "food_tags": (
                "chicken options, "
                "vegetarian"
            )
        },
        request=request,
    )

    assert (
        score
        == 1.0
    )


def test_area_match_prefers_back_bay() -> None:
    request = make_request()

    back_bay = area_match_score(
        metadata={
            "area": "Back Bay",
        },
        request=request,
    )

    downtown = area_match_score(
        metadata={
            "area": "Downtown",
        },
        request=request,
    )

    assert (
        back_bay
        > downtown
    )


def test_budget_fit_penalizes_expensive_venue() -> None:
    request = make_request()

    affordable = budget_fit_score(
        metadata={
            "estimated_cost_per_person": (
                30
            ),
        },
        request=request,
    )

    expensive = budget_fit_score(
        metadata={
            "estimated_cost_per_person": (
                120
            ),
        },
        request=request,
    )

    assert affordable == 1.0

    assert expensive < affordable


def test_proximity_prefers_nearby_coordinates() -> None:
    start = (
        42.3493,
        -71.0810,
    )

    near = proximity_score(
        metadata={
            "latitude": 42.3500,
            "longitude": -71.0800,
        },
        start_coordinates=start,
    )

    far = proximity_score(
        metadata={
            "latitude": 42.3000,
            "longitude": -71.1500,
        },
        start_coordinates=start,
    )

    assert near > far


def test_score_returns_explainable_breakdown() -> None:
    request = make_request()

    result = make_result(
        document_id="good",
        name="Back Bay Chicken",
        area="Back Bay",
        food_tags="chicken options",
        vibe="chill, foodie",
        cost=30,
        latitude=42.3500,
        longitude=-71.0800,
        distance=0.9,
    )

    scored = score_retrieval_result(
        result=result,
        request=request,
        desired_category="restaurant",
        start_coordinates=(
            42.3493,
            -71.0810,
        ),
    )

    assert (
        scored.final_score
        > 0
    )

    assert (
        scored.breakdown.food
        == 1.0
    )

    assert (
        scored.breakdown.area
        == 1.0
    )

    assert (
        "food preference match"
        in scored.reasons
    )


def test_hybrid_ranking_can_beat_raw_semantic_order() -> None:
    request = make_request()

    semantic_winner = make_result(
        document_id="downtown",
        name="Downtown Generic",
        area="Downtown",
        food_tags="vegetarian",
        vibe="indoor",
        cost=55,
        latitude=42.3600,
        longitude=-71.0600,
        distance=0.70,
    )

    structured_winner = make_result(
        document_id="back-bay",
        name="Back Bay Chicken",
        area="Back Bay",
        food_tags=(
            "chicken options"
        ),
        vibe="chill, foodie",
        cost=30,
        latitude=42.3500,
        longitude=-71.0800,
        distance=0.90,
    )

    ranked = rerank_results(
        results=[
            semantic_winner,
            structured_winner,
        ],
        request=request,
        desired_category="restaurant",
        start_coordinates=(
            42.3493,
            -71.0810,
        ),
    )

    assert (
        ranked[0]
        .result
        .document_id
        == "back-bay"
    )


def test_category_match_can_demote_wrong_type() -> None:
    request = make_request()

    activity = make_result(
        document_id="activity",
        name="Fun Museum",
        area="Back Bay",
        food_tags="chicken",
        vibe="chill",
        cost=20,
        latitude=42.3500,
        longitude=-71.0800,
        distance=0.50,
        category="activity",
    )

    restaurant = make_result(
        document_id="restaurant",
        name="Chicken Restaurant",
        area="Back Bay",
        food_tags="chicken",
        vibe="chill",
        cost=30,
        latitude=42.3500,
        longitude=-71.0800,
        distance=0.60,
        category="restaurant",
    )

    ranked = rerank_results(
        results=[
            activity,
            restaurant,
        ],
        request=request,
        desired_category="restaurant",
        start_coordinates=(
            42.3493,
            -71.0810,
        ),
    )

    assert (
        ranked[0]
        .result
        .document_id
        == "restaurant"
    )


def test_rerank_limit_is_applied() -> None:
    request = make_request()

    results = [
        make_result(
            document_id=str(index),
            name=f"Venue {index}",
            area="Back Bay",
            food_tags="chicken",
            vibe="chill",
            cost=25,
            latitude=42.3500,
            longitude=-71.0800,
            distance=(
                0.8
                + index * 0.01
            ),
        )
        for index
        in range(5)
    ]

    ranked = rerank_results(
        results=results,
        request=request,
        limit=2,
    )

    assert (
        len(ranked)
        == 2
    )
