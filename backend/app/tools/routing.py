from __future__ import annotations

import os
from math import (
    asin,
    ceil,
    cos,
    radians,
    sin,
    sqrt,
)
from typing import Any

import requests

from backend.app.models import (
    RoutePoint,
    RouteResult,
    TransportMode,
)


GEOAPIFY_ROUTING_URL = (
    "https://api.geoapify.com/v1/routing"
)


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

    latitude_difference = (
        lat_b - lat_a
    )

    longitude_difference = (
        lon_b - lon_a
    )

    value = (
        sin(latitude_difference / 2) ** 2
        + cos(lat_a)
        * cos(lat_b)
        * sin(
            longitude_difference / 2
        )
        ** 2
    )

    central_angle = 2 * asin(
        sqrt(value)
    )

    return (
        earth_radius_km
        * central_angle
    )


def estimate_travel_minutes(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
    transport: TransportMode,
) -> int:
    """
    V1 fallback travel-time estimate.

    V2 keeps this function so planning continues to work when
    the live routing provider is unavailable.
    """
    distance_km = (
        haversine_distance_km(
            latitude_a=latitude_a,
            longitude_a=longitude_a,
            latitude_b=latitude_b,
            longitude_b=longitude_b,
        )
    )

    if distance_km < 0.15:
        return 3

    if transport == "walking":
        route_distance_km = (
            distance_km * 1.25
        )

        speed_km_per_hour = 4.8
        wait_minutes = 0

    elif transport == "driving":
        route_distance_km = (
            distance_km * 1.3
        )

        speed_km_per_hour = 24
        wait_minutes = 4

    else:
        route_distance_km = (
            distance_km * 1.35
        )

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


def estimate_route_result(
    *,
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
    transport: TransportMode,
) -> RouteResult:
    """
    Convert the existing V1 estimate into the new V2 RouteResult
    structure.
    """
    duration_minutes = (
        estimate_travel_minutes(
            latitude_a=latitude_a,
            longitude_a=longitude_a,
            latitude_b=latitude_b,
            longitude_b=longitude_b,
            transport=transport,
        )
    )

    straight_line_km = (
        haversine_distance_km(
            latitude_a=latitude_a,
            longitude_a=longitude_a,
            latitude_b=latitude_b,
            longitude_b=longitude_b,
        )
    )

    if transport == "walking":
        route_multiplier = 1.25

    elif transport == "driving":
        route_multiplier = 1.3

    else:
        route_multiplier = 1.35

    estimated_distance_meters = int(
        straight_line_km
        * route_multiplier
        * 1000
    )

    return RouteResult(
        duration_minutes=(
            duration_minutes
        ),
        distance_meters=(
            estimated_distance_meters
        ),
        mode=transport,
        geometry=[
            RoutePoint(
                latitude=latitude_a,
                longitude=longitude_a,
            ),
            RoutePoint(
                latitude=latitude_b,
                longitude=longitude_b,
            ),
        ],
        provider="estimate",
        is_live=False,
        fallback_used=True,
    )


def geoapify_mode(
    transport: TransportMode,
) -> str:
    """
    Map PlanPilot transport modes to Geoapify routing modes.

    Geoapify supports road-based walking and driving routing.
    Public-transit support is kept on the local fallback for this
    first V2 milestone until we introduce a dedicated transit
    routing strategy.
    """
    mapping = {
        "walking": "walk",
        "driving": "drive",
    }

    return mapping.get(
        transport,
        "walk",
    )


def _extract_geometry_points(
    geometry: dict[str, Any] | None,
) -> list[RoutePoint]:
    """
    Convert GeoJSON LineString or MultiLineString coordinates
    into PlanPilot RoutePoint objects.
    """
    if not geometry:
        return []

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if not isinstance(
        coordinates,
        list,
    ):
        return []

    raw_points: list[
        list[float]
    ] = []

    if geometry_type == "LineString":
        raw_points = [
            point
            for point in coordinates
            if (
                isinstance(
                    point,
                    list,
                )
                and len(point) >= 2
            )
        ]

    elif (
        geometry_type
        == "MultiLineString"
    ):
        for segment in coordinates:
            if not isinstance(
                segment,
                list,
            ):
                continue

            for point in segment:
                if (
                    isinstance(
                        point,
                        list,
                    )
                    and len(point) >= 2
                ):
                    raw_points.append(
                        point
                    )

    route_points: list[
        RoutePoint
    ] = []

    for point in raw_points:
        longitude = point[0]
        latitude = point[1]

        if not isinstance(
            latitude,
            (int, float),
        ):
            continue

        if not isinstance(
            longitude,
            (int, float),
        ):
            continue

        route_points.append(
            RoutePoint(
                latitude=float(
                    latitude
                ),
                longitude=float(
                    longitude
                ),
            )
        )

    return route_points


def _parse_geoapify_route(
    data: dict[str, Any],
    *,
    transport: TransportMode,
) -> RouteResult | None:
    """
    Normalize a Geoapify GeoJSON routing response.
    """
    features = data.get(
        "features"
    )

    if not isinstance(
        features,
        list,
    ):
        return None

    if not features:
        return None

    feature = features[0]

    if not isinstance(
        feature,
        dict,
    ):
        return None

    properties = feature.get(
        "properties",
        {},
    )

    if not isinstance(
        properties,
        dict,
    ):
        return None

    time_seconds = properties.get(
        "time"
    )

    distance_meters = (
        properties.get(
            "distance"
        )
    )

    if not isinstance(
        time_seconds,
        (int, float),
    ):
        return None

    if not isinstance(
        distance_meters,
        (int, float),
    ):
        return None

    duration_minutes = max(
        1,
        ceil(
            float(time_seconds)
            / 60
        ),
    )

    geometry = feature.get(
        "geometry"
    )

    parsed_geometry = (
        _extract_geometry_points(
            geometry
            if isinstance(
                geometry,
                dict,
            )
            else None
        )
    )

    return RouteResult(
        duration_minutes=(
            duration_minutes
        ),
        distance_meters=max(
            0,
            int(distance_meters),
        ),
        mode=transport,
        geometry=parsed_geometry,
        provider="geoapify",
        is_live=True,
        fallback_used=False,
    )


def get_geoapify_route(
    *,
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
    transport: TransportMode,
) -> RouteResult | None:
    """
    Request one live route from Geoapify.

    Returns None when live routing is unavailable so the caller
    can fall back safely.
    """
    api_key = os.getenv(
        "GEOAPIFY_API_KEY",
        "",
    ).strip()

    if not api_key:
        return None

    # Public transit remains on fallback during V2.1.
    if transport == "public_transit":
        return None

    timeout_seconds = float(
        os.getenv(
            "ROUTING_TIMEOUT_SECONDS",
            "10",
        )
    )

    waypoints = (
        f"{latitude_a},"
        f"{longitude_a}"
        "|"
        f"{latitude_b},"
        f"{longitude_b}"
    )

    params = {
        "waypoints": waypoints,
        "mode": geoapify_mode(
            transport
        ),
        "apiKey": api_key,
    }

    try:
        response = requests.get(
            GEOAPIFY_ROUTING_URL,
            params=params,
            timeout=timeout_seconds,
        )

        response.raise_for_status()

        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ):
        return None

    if not isinstance(
        data,
        dict,
    ):
        return None

    return _parse_geoapify_route(
        data,
        transport=transport,
    )


def get_route(
    *,
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
    transport: TransportMode,
) -> RouteResult:
    """
    Main routing interface used by PlanPilot V2.

    Routing strategy:

    1. Try the configured live routing provider.
    2. Fall back to the V1 deterministic estimate when live
       routing fails or is unavailable.
    """
    provider = os.getenv(
        "ROUTING_PROVIDER",
        "geoapify",
    ).strip().lower()

    live_route: (
        RouteResult | None
    ) = None

    if provider == "geoapify":
        live_route = (
            get_geoapify_route(
                latitude_a=(
                    latitude_a
                ),
                longitude_a=(
                    longitude_a
                ),
                latitude_b=(
                    latitude_b
                ),
                longitude_b=(
                    longitude_b
                ),
                transport=transport,
            )
        )

    if live_route is not None:
        return live_route

    return estimate_route_result(
        latitude_a=latitude_a,
        longitude_a=longitude_a,
        latitude_b=latitude_b,
        longitude_b=longitude_b,
        transport=transport,
    )
