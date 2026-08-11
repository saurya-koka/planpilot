from backend.app.models import RouteResult
from backend.app.tools.routing import (
    _extract_geometry_points,
    _parse_geoapify_route,
    estimate_route_result,
    geoapify_mode,
)


def test_geoapify_mode_mapping() -> None:
    assert geoapify_mode("walking") == "walk"
    assert geoapify_mode("driving") == "drive"


def test_estimate_route_result_returns_fallback() -> None:
    result = estimate_route_result(
        latitude_a=42.3507,
        longitude_a=-71.0797,
        latitude_b=42.3619,
        longitude_b=-71.0864,
        transport="walking",
    )

    assert isinstance(result, RouteResult)
    assert result.duration_minutes > 0
    assert result.distance_meters > 0
    assert result.provider == "estimate"
    assert result.is_live is False
    assert result.fallback_used is True
    assert len(result.geometry) == 2


def test_extract_linestring_geometry() -> None:
    geometry = {
        "type": "LineString",
        "coordinates": [
            [-71.0797, 42.3507],
            [-71.0864, 42.3619],
        ],
    }

    points = _extract_geometry_points(
        geometry
    )

    assert len(points) == 2
    assert points[0].latitude == 42.3507
    assert points[0].longitude == -71.0797


def test_extract_multilinestring_geometry() -> None:
    geometry = {
        "type": "MultiLineString",
        "coordinates": [
            [
                [-71.0797, 42.3507],
                [-71.0830, 42.3560],
            ],
            [
                [-71.0830, 42.3560],
                [-71.0864, 42.3619],
            ],
        ],
    }

    points = _extract_geometry_points(
        geometry
    )

    assert len(points) == 4


def test_parse_geoapify_route() -> None:
    response = {
        "features": [
            {
                "properties": {
                    "time": 720,
                    "distance": 2400,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-71.0797, 42.3507],
                        [-71.0864, 42.3619],
                    ],
                },
            }
        ]
    }

    result = _parse_geoapify_route(
        response,
        transport="walking",
    )

    assert result is not None
    assert result.duration_minutes == 12
    assert result.distance_meters == 2400
    assert result.provider == "geoapify"
    assert result.is_live is True
    assert result.fallback_used is False
    assert len(result.geometry) == 2


def test_parse_geoapify_route_rejects_invalid_response() -> None:
    result = _parse_geoapify_route(
        {"features": []},
        transport="walking",
    )

    assert result is None
