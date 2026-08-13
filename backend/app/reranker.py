from __future__ import annotations

import math
from dataclasses import (
    dataclass,
    field,
)
from typing import Any

from .models import (
    PlanRequest,
)
from .vector_store import (
    RetrievalResult,
)


SEMANTIC_WEIGHT = 0.35
CATEGORY_WEIGHT = 0.15
FOOD_WEIGHT = 0.15
VIBE_WEIGHT = 0.10
AREA_WEIGHT = 0.10
BUDGET_WEIGHT = 0.05
PROXIMITY_WEIGHT = 0.10


@dataclass
class HybridScoreBreakdown:
    """
    Explainable score components for one retrieved venue.

    Every component is normalized to the range [0, 1].
    """

    semantic: float = 0.0
    category: float = 0.0
    food: float = 0.0
    vibe: float = 0.0
    area: float = 0.0
    budget: float = 0.0
    proximity: float = 0.0


@dataclass
class RerankedResult:
    """
    One retrieval result after deterministic hybrid reranking.
    """

    result: RetrievalResult

    final_score: float

    breakdown: HybridScoreBreakdown

    reasons: list[str] = field(
        default_factory=list,
    )


def clamp_score(
    value: float,
) -> float:
    """
    Clamp a score into the [0, 1] range.
    """

    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def normalize_text(
    value: str,
) -> str:
    """
    Normalize text for deterministic structured matching.
    """

    return (
        value
        .strip()
        .lower()
        .replace(",", " ")
        .replace("/", " ")
        .replace("-", " ")
        .replace("_", " ")
    )


def tokenize(
    value: str,
) -> set[str]:
    """
    Convert text into a normalized token set.
    """

    return {
        token
        for token
        in normalize_text(
            value
        ).split()
        if token
    }


def semantic_score_from_distance(
    distance: float | None,
) -> float:
    """
    Convert vector distance into a bounded similarity score.

    Chroma's exact distance scale can vary with collection settings.
    Using 1 / (1 + distance) gives us a stable monotonic score:
    smaller distance -> larger semantic score.
    """

    if distance is None:
        return 0.0

    if distance < 0:
        distance = 0.0

    return clamp_score(
        1.0
        / (
            1.0
            + distance
        )
    )


def metadata_text(
    metadata: dict[
        str,
        Any,
    ],
    key: str,
) -> str:
    """
    Safely read textual metadata.
    """

    value = metadata.get(
        key,
        "",
    )

    if value is None:
        return ""

    return str(
        value
    )


def overlap_score(
    requested_values: list[str],
    candidate_text: str,
) -> float:
    """
    Score how well candidate text matches requested concepts.

    A phrase such as "chicken options" will match a request containing
    "chicken", while exact normalized phrases also receive credit.
    """

    if not requested_values:
        return 1.0

    candidate_normalized = (
        normalize_text(
            candidate_text
        )
    )

    candidate_tokens = tokenize(
        candidate_text
    )

    matched = 0

    for requested in requested_values:
        requested_normalized = (
            normalize_text(
                requested
            )
        )

        requested_tokens = tokenize(
            requested
        )

        if not requested_normalized:
            continue

        if (
            requested_normalized
            in candidate_normalized
        ):
            matched += 1
            continue

        if (
            requested_tokens
            and requested_tokens.intersection(
                candidate_tokens
            )
        ):
            matched += 1

    return clamp_score(
        matched
        / max(
            1,
            len(
                requested_values
            ),
        )
    )


def category_match_score(
    *,
    metadata: dict[
        str,
        Any,
    ],
    desired_category: (
        str
        | None
    ),
) -> float:
    """
    Reward the requested venue category.

    When no explicit category is being reranked, the component becomes
    neutral instead of penalizing the result.
    """

    if not desired_category:
        return 1.0

    candidate = normalize_text(
        metadata_text(
            metadata,
            "category",
        )
    )

    desired = normalize_text(
        desired_category
    )

    return (
        1.0
        if candidate == desired
        else 0.0
    )


def food_match_score(
    *,
    metadata: dict[
        str,
        Any,
    ],
    request: PlanRequest,
) -> float:
    """
    Measure food-preference overlap.
    """

    if not request.food_preferences:
        return 1.0

    food_tags = metadata_text(
        metadata,
        "food_tags",
    )

    return overlap_score(
        request.food_preferences,
        food_tags,
    )


def vibe_match_score(
    *,
    metadata: dict[
        str,
        Any,
    ],
    request: PlanRequest,
) -> float:
    """
    Measure requested-vibe overlap.
    """

    if not request.vibe:
        return 1.0

    vibe = metadata_text(
        metadata,
        "vibe",
    )

    return overlap_score(
        request.vibe,
        vibe,
    )


def area_match_score(
    *,
    metadata: dict[
        str,
        Any,
    ],
    request: PlanRequest,
) -> float:
    """
    Reward venues in the user's requested starting area.

    Partial containment receives some credit so metadata such as
    "Back Bay, Boston" can match "Back Bay".
    """

    candidate = normalize_text(
        metadata_text(
            metadata,
            "area",
        )
    )

    requested = normalize_text(
        request.start_area
    )

    if (
        not candidate
        or not requested
    ):
        return 0.0

    if candidate == requested:
        return 1.0

    if (
        candidate in requested
        or requested in candidate
    ):
        return 0.8

    return 0.0


def budget_fit_score(
    *,
    metadata: dict[
        str,
        Any,
    ],
    request: PlanRequest,
) -> float:
    """
    Reward venues that fit the user's approximate per-person budget.

    This is not itinerary-level budget validation. It is only a
    retrieval ranking signal.
    """

    raw_cost = metadata.get(
        "estimated_cost_per_person"
    )

    if raw_cost is None:
        return 0.5

    try:
        venue_cost = float(
            raw_cost
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.5

    per_person_budget = (
        request.budget_total
        / request.party_size
    )

    if venue_cost <= 0:
        return 1.0

    if venue_cost <= per_person_budget:
        return 1.0

    ratio = (
        per_person_budget
        / venue_cost
    )

    return clamp_score(
        ratio
    )


def haversine_distance_km(
    *,
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """
    Calculate straight-line geographic distance.

    This intentionally stays local to the reranker so scoring does not
    trigger routing APIs or network calls.
    """

    earth_radius_km = 6371.0088

    lat_a = math.radians(
        latitude_a
    )

    lat_b = math.radians(
        latitude_b
    )

    delta_lat = math.radians(
        latitude_b
        - latitude_a
    )

    delta_lon = math.radians(
        longitude_b
        - longitude_a
    )

    haversine = (
        math.sin(
            delta_lat / 2
        ) ** 2
        + math.cos(
            lat_a
        )
        * math.cos(
            lat_b
        )
        * math.sin(
            delta_lon / 2
        ) ** 2
    )

    central_angle = (
        2
        * math.atan2(
            math.sqrt(
                haversine
            ),
            math.sqrt(
                1
                - haversine
            ),
        )
    )

    return (
        earth_radius_km
        * central_angle
    )


def proximity_score(
    *,
    metadata: dict[
        str,
        Any,
    ],
    start_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ),
) -> float:
    """
    Reward venues geographically close to the starting point.

    <= 1 km  -> 1.00
    2 km     -> 0.80
    5 km     -> 0.40
    10+ km   -> 0.00

    Missing coordinates receive a neutral-ish score rather than a
    complete penalty.
    """

    if start_coordinates is None:
        return 0.5

    raw_latitude = metadata.get(
        "latitude"
    )

    raw_longitude = metadata.get(
        "longitude"
    )

    if (
        raw_latitude is None
        or raw_longitude is None
    ):
        return 0.5

    try:
        latitude = float(
            raw_latitude
        )

        longitude = float(
            raw_longitude
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0.5

    distance = haversine_distance_km(
        latitude_a=(
            start_coordinates[0]
        ),
        longitude_a=(
            start_coordinates[1]
        ),
        latitude_b=latitude,
        longitude_b=longitude,
    )

    if distance <= 1.0:
        return 1.0

    if distance <= 2.0:
        return 0.8

    if distance <= 5.0:
        return 0.4

    if distance <= 10.0:
        return 0.2

    return 0.0


def score_retrieval_result(
    *,
    result: RetrievalResult,
    request: PlanRequest,
    desired_category: (
        str
        | None
    ) = None,
    start_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ) = None,
) -> RerankedResult:
    """
    Combine semantic retrieval similarity with structured PlanPilot
    constraints.
    """

    metadata = (
        result.metadata
        or {}
    )

    breakdown = HybridScoreBreakdown(
        semantic=(
            semantic_score_from_distance(
                result.distance
            )
        ),
        category=(
            category_match_score(
                metadata=metadata,
                desired_category=(
                    desired_category
                ),
            )
        ),
        food=(
            food_match_score(
                metadata=metadata,
                request=request,
            )
        ),
        vibe=(
            vibe_match_score(
                metadata=metadata,
                request=request,
            )
        ),
        area=(
            area_match_score(
                metadata=metadata,
                request=request,
            )
        ),
        budget=(
            budget_fit_score(
                metadata=metadata,
                request=request,
            )
        ),
        proximity=(
            proximity_score(
                metadata=metadata,
                start_coordinates=(
                    start_coordinates
                ),
            )
        ),
    )

    final_score = (
        breakdown.semantic
        * SEMANTIC_WEIGHT

        + breakdown.category
        * CATEGORY_WEIGHT

        + breakdown.food
        * FOOD_WEIGHT

        + breakdown.vibe
        * VIBE_WEIGHT

        + breakdown.area
        * AREA_WEIGHT

        + breakdown.budget
        * BUDGET_WEIGHT

        + breakdown.proximity
        * PROXIMITY_WEIGHT
    )

    reasons: list[
        str
    ] = []

    if breakdown.category >= 1.0:
        reasons.append(
            "category match"
        )

    if breakdown.food > 0:
        reasons.append(
            "food preference match"
        )

    if breakdown.vibe > 0:
        reasons.append(
            "vibe match"
        )

    if breakdown.area >= 0.8:
        reasons.append(
            "area match"
        )

    if breakdown.budget >= 1.0:
        reasons.append(
            "within approximate budget"
        )

    if breakdown.proximity >= 0.8:
        reasons.append(
            "close to starting point"
        )

    return RerankedResult(
        result=result,
        final_score=round(
            final_score,
            6,
        ),
        breakdown=breakdown,
        reasons=reasons,
    )


def rerank_results(
    *,
    results: list[
        RetrievalResult
    ],
    request: PlanRequest,
    desired_category: (
        str
        | None
    ) = None,
    start_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ) = None,
    limit: (
        int
        | None
    ) = None,
) -> list[
    RerankedResult
]:
    """
    Hybrid-rerank semantic retrieval results.

    Higher final scores rank first. Original semantic distance is used
    as a stable secondary tie-breaker.
    """

    scored = [
        score_retrieval_result(
            result=result,
            request=request,
            desired_category=(
                desired_category
            ),
            start_coordinates=(
                start_coordinates
            ),
        )
        for result
        in results
    ]

    scored.sort(
        key=lambda item: (
            -item.final_score,
            (
                item.result.distance
                if (
                    item.result.distance
                    is not None
                )
                else float(
                    "inf"
                )
            ),
            item.result.document_id,
        )
    )

    if limit is None:
        return scored

    if limit < 1:
        raise ValueError(
            "limit must be at least 1."
        )

    return scored[
        :limit
    ]
