from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TransportMode = Literal["public_transit", "walking", "driving"]


class PlanRequest(BaseModel):
    city: str = "Boston"
    start_area: str = "Davis Square"
    date: str = "Friday"
    start_time: str = "17:00"
    budget_total: float = Field(default=200, gt=0)
    party_size: int = Field(default=2, ge=1, le=12)
    transport: TransportMode = "public_transit"
    vibe: list[str] = Field(default_factory=lambda: ["romantic", "fun"])
    must_include: list[str] = Field(
        default_factory=lambda: ["activity", "dinner"]
    )
    food_preferences: list[str] = Field(
        default_factory=lambda: ["chicken options"]
    )
    max_leg_minutes: int = Field(default=30, ge=5, le=180)


class Venue(BaseModel):
    name: str
    category: Literal["activity", "restaurant", "dessert"]
    area: str
    estimated_cost_per_person: float
    duration_minutes: int
    vibe: list[str]
    food_tags: list[str] = Field(default_factory=list)


class Stop(BaseModel):
    name: str
    category: str
    area: str
    estimated_cost: float
    duration_minutes: int


class Itinerary(BaseModel):
    label: str
    title: str
    stops: list[Stop]
    total_cost: float
    total_duration_minutes: int
    estimated_travel_minutes: int
    score: float
    reasons: list[str]
    warnings: list[str]


class NaturalLanguageRequest(BaseModel):
    text: str
    start_area: str = "Davis Square"
    food_preferences: list[str] = Field(default_factory=list)


class ParsedPlanRequest(BaseModel):
    city: str = "Boston"
    budget: float = Field(default=200, gt=0)
    party_size: int = Field(default=2, ge=1, le=12)
    max_travel_minutes: int = Field(default=30, ge=5, le=180)
    vibe: str = "romantic"
    include_activity: bool = True
    include_dinner: bool = True
    include_dessert: bool = False
    transportation: str = "public_transit"
    start_time: str | None = None
    date_text: str | None = None
    food_preferences: list[str] = Field(default_factory=list)

class PlaceSearchRequest(BaseModel):
    query: str
    city: str = "Boston"
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=20)


class PlaceResult(BaseModel):
    place_id: str
    name: str
    formatted_address: str
    latitude: float
    longitude: float
    categories: list[str] = Field(default_factory=list)
    distance_meters: int | None = None
    opening_hours: str | None = None
    website: str | None = None
    source: str = "geoapify"
