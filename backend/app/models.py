from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from typing import Optional



class PlanRequest(BaseModel):
    city: str = "Boston"
    start_area: str = "Davis Square"
    date: str = "Friday"
    start_time: str = "17:00"
    budget_total: float = Field(default=200, gt=0)
    party_size: int = Field(default=2, ge=1, le=12)
    transport: Literal["public_transit", "walking", "driving"] = "public_transit"
    vibe: list[str] = Field(default_factory=lambda: ["romantic", "fun"])
    must_include: list[str] = Field(default_factory=lambda: ["activity", "dinner"])
    food_preferences: list[str] = Field(default_factory=lambda: ["chicken options"])
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


class ParsedPlanRequest(BaseModel):
    city: str = "Boston"
    budget: float = 200
    party_size: int = 2
    max_travel_minutes: int = 30
    vibe: str = "romantic"
    include_activity: bool = True
    include_dinner: bool = True
    include_dessert: bool = False
    transportation: str = "public_transit"
    start_time: Optional[str] = None
    date_text: Optional[str] = None
