from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TransportMode = Literal[
    "public_transit",
    "walking",
    "driving",
]


VenueCategory = Literal[
    "activity",
    "restaurant",
    "dessert",
]


ValidationSeverity = Literal[
    "info",
    "warning",
    "error",
]


ValidationCode = Literal[
    "budget_exceeded",
    "travel_leg_too_long",
    "venue_closed",
    "opening_hours_unknown",
    "route_fallback_used",
]


RepairStrategy = Literal[
    "replace_expensive_venue",
    "replace_distant_venue",
    "replace_closed_venue",
    "no_action",
]


class ValidationFailure(BaseModel):
    """
    One machine-readable validation issue.

    These objects are consumed by the repair agent in V2.4.
    """

    code: ValidationCode

    severity: ValidationSeverity

    message: str

    details: dict[str, object] = Field(
        default_factory=dict,
    )


class ValidationResult(BaseModel):
    """
    Result returned by the deterministic itinerary validator.
    """

    is_valid: bool

    failures: list[
        ValidationFailure
    ] = Field(
        default_factory=list,
    )


class PlanRequest(BaseModel):
    city: str = "Boston"

    start_area: str = "Davis Square"

    date: str = "Friday"

    start_time: str = "17:00"

    budget_total: float = Field(
        default=200,
        gt=0,
    )

    party_size: int = Field(
        default=2,
        ge=1,
        le=12,
    )

    transport: TransportMode = (
        "public_transit"
    )

    vibe: list[str] = Field(
        default_factory=lambda: [
            "romantic",
            "fun",
        ]
    )

    must_include: list[str] = Field(
        default_factory=lambda: [
            "activity",
            "dinner",
        ]
    )

    food_preferences: list[str] = Field(
        default_factory=lambda: [
            "chicken options"
        ]
    )

    max_leg_minutes: int = Field(
        default=30,
        ge=5,
        le=180,
    )


class Venue(BaseModel):
    """
    Normalized venue used by the itinerary planner.

    A venue may come from the sample dataset or from a live
    provider such as Geoapify.
    """

    name: str

    category: VenueCategory

    area: str

    estimated_cost_per_person: float = Field(
        ge=0,
    )

    duration_minutes: int = Field(
        ge=1,
    )

    vibe: list[str] = Field(
        default_factory=list,
    )

    food_tags: list[str] = Field(
        default_factory=list,
    )

    latitude: float | None = None

    longitude: float | None = None

    formatted_address: (
        str
        | None
    ) = None

    website: (
        str
        | None
    ) = None

    opening_hours: (
        str
        | None
    ) = None

    source: str = "sample"


class Stop(BaseModel):
    """
    One stop inside a generated itinerary.
    """

    name: str

    category: str

    area: str

    estimated_cost: float = Field(
        ge=0,
    )

    duration_minutes: int = Field(
        ge=1,
    )

    latitude: float | None = None

    longitude: float | None = None

    formatted_address: (
        str
        | None
    ) = None

    website: (
        str
        | None
    ) = None

    opening_hours: (
        str
        | None
    ) = None

    source: str = "sample"


class RoutePoint(BaseModel):
    latitude: float

    longitude: float


class RouteResult(BaseModel):
    """
    Normalized route returned by a routing provider.

    PlanPilot can therefore change routing providers later without
    changing the planner.
    """

    duration_minutes: int = Field(
        ge=0,
    )

    distance_meters: int = Field(
        ge=0,
    )

    mode: TransportMode

    geometry: list[
        RoutePoint
    ] = Field(
        default_factory=list,
    )

    provider: str

    is_live: bool = True

    fallback_used: bool = False


class RouteLeg(BaseModel):
    """
    Travel leg connecting the start point or two itinerary stops.
    """

    from_name: str

    to_name: str

    duration_minutes: int = Field(
        ge=0,
    )

    distance_meters: int = Field(
        ge=0,
    )

    mode: TransportMode

    geometry: list[
        RoutePoint
    ] = Field(
        default_factory=list,
    )

    provider: str

    fallback_used: bool = False


class Itinerary(BaseModel):
    label: str

    title: str

    stops: list[
        Stop
    ]

    total_cost: float

    total_duration_minutes: int

    estimated_travel_minutes: int

    score: float

    route_legs: list[
        RouteLeg
    ] = Field(
        default_factory=list,
    )

    validation_failures: list[
        ValidationFailure
    ] = Field(
        default_factory=list,
    )

    reasons: list[
        str
    ]

    warnings: list[
        str
    ]


class RepairAction(BaseModel):
    """
    One concrete repair decision made by the agent.

    Example:
        budget_exceeded
            ->
        replace_expensive_venue
            ->
        replace Restaurant A with Restaurant B
    """

    failure_code: ValidationCode

    strategy: RepairStrategy

    target_name: (
        str
        | None
    ) = None

    replacement_name: (
        str
        | None
    ) = None

    rationale: str

    metadata: dict[
        str,
        object,
    ] = Field(
        default_factory=dict,
    )


class RepairAttempt(BaseModel):
    """
    Record of one complete repair iteration.

    This lets PlanPilot explain what the agent changed and whether
    the change improved the itinerary.
    """

    attempt_number: int = Field(
        ge=1,
    )

    input_plan_title: str

    failure_codes: list[
        ValidationCode
    ] = Field(
        default_factory=list,
    )

    actions: list[
        RepairAction
    ] = Field(
        default_factory=list,
    )

    output_plan_title: (
        str
        | None
    ) = None

    remaining_failures: list[
        ValidationFailure
    ] = Field(
        default_factory=list,
    )

    success: bool = False


class RepairResult(BaseModel):
    """
    Final result of the bounded agentic repair process.

    The repair loop may succeed before reaching the attempt limit,
    or exhaust all allowed attempts while preserving a full trace.
    """

    success: bool

    original_itinerary: Itinerary

    final_itinerary: (
        Itinerary
        | None
    ) = None

    attempts: list[
        RepairAttempt
    ] = Field(
        default_factory=list,
    )

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
    )

    exhausted: bool = False


class NaturalLanguageRequest(
    BaseModel
):
    text: str

    start_area: str = (
        "Davis Square"
    )

    food_preferences: list[
        str
    ] = Field(
        default_factory=list,
    )


class ParsedPlanRequest(
    BaseModel
):
    city: str = "Boston"

    budget: float = Field(
        default=200,
        gt=0,
    )

    party_size: int = Field(
        default=2,
        ge=1,
        le=12,
    )

    max_travel_minutes: int = Field(
        default=30,
        ge=5,
        le=180,
    )

    vibes: list[
        str
    ] = Field(
        default_factory=lambda: [
            "fun"
        ],
    )

    include_activity: bool = True

    include_dinner: bool = True

    include_dessert: bool = False

    transportation: str = (
        "public_transit"
    )

    start_time: (
        str
        | None
    ) = None

    date_text: (
        str
        | None
    ) = None

    food_preferences: list[
        str
    ] = Field(
        default_factory=list,
    )


class PlaceSearchRequest(
    BaseModel
):
    query: str

    city: str = "Boston"

    category: (
        str
        | None
    ) = None

    limit: int = Field(
        default=10,
        ge=1,
        le=20,
    )


class PlaceResult(BaseModel):
    """
    Normalized result returned by a live place provider.
    """

    place_id: str

    name: str

    formatted_address: str

    latitude: float

    longitude: float

    categories: list[
        str
    ] = Field(
        default_factory=list,
    )

    city: (
        str
        | None
    ) = None

    district: (
        str
        | None
    ) = None

    suburb: (
        str
        | None
    ) = None

    postcode: (
        str
        | None
    ) = None

    state: (
        str
        | None
    ) = None

    country: (
        str
        | None
    ) = None

    distance_meters: (
        int
        | None
    ) = None

    opening_hours: (
        str
        | None
    ) = None

    website: (
        str
        | None
    ) = None

    source: str = (
        "geoapify"
    )
