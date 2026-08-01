from __future__ import annotations

from math import asin, ceil, cos, radians, sin, sqrt

from backend.app.models import TransportMode


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """
    Calculate straight-line distance between two coordinates.

    The returned distance is in kilometers.
    """
    earth_radius_km = 6371.0

    lat_a = radians(latitude_a)
    lon_a = radians(longitude_a)
    lat_b = radians(latitude_b)
    lon_b = radians(longitude_b)

    latitude_difference = lat_b - lat_a
    longitude_difference = lon_b - lon_a

    value = (
        sin(latitude_difference / 2) ** 2
        + cos(lat_a)
        * cos(lat_b)
        * sin(longitude_difference / 2) ** 2
    )

    central_angle = 2 * asin(
        sqrt(value)
    )

    return earth_radius_km * central_angle


def estimate_travel_minutes(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
    transport: TransportMode,
) -> int:
    """
    Estimate travel time using straight-line distance.

    These are temporary estimates until PlanPilot integrates a
    live routing provider.
    """
    distance_km = haversine_distance_km(
        latitude_a=latitude_a,
        longitude_a=longitude_a,
        latitude_b=latitude_b,
        longitude_b=longitude_b,
    )

    if distance_km < 0.15:
        return 3

    if transport == "walking":
        # Walking routes are normally longer than straight-line
        # distance, so apply a route-distance multiplier.
        route_distance_km = distance_km * 1.25
        speed_km_per_hour = 4.8
        wait_minutes = 0

    elif transport == "driving":
        route_distance_km = distance_km * 1.3
        speed_km_per_hour = 24
        wait_minutes = 4

    else:
        # Public transit includes indirect routing and average
        # waiting/transfer time.
        route_distance_km = distance_km * 1.35
        speed_km_per_hour = 18
        wait_minutes = 8

    movement_minutes = (
        route_distance_km
        / speed_km_per_hour
        * 60
    )

    return max(
        3,
        ceil(
            movement_minutes
            + wait_minutes
        ),
    )
