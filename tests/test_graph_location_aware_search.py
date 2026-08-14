from __future__ import annotations

from backend.app import (
    graph_nodes,
)
from backend.app.models import (
    PlanRequest,
)


def test_graph_search_uses_start_coordinates(
    monkeypatch,
) -> None:
    captured: dict[
        str,
        object,
    ] = {}

    request = PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="18:00",
        budget_total=70,
        party_size=2,
        transport="walking",
        vibe=[
            "budget",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=30,
    )

    def fake_search_places(
        *,
        query,
        city,
        category,
        limit,
        center_coordinates=None,
    ):
        captured[
            "query"
        ] = query

        captured[
            "city"
        ] = city

        captured[
            "category"
        ] = category

        captured[
            "limit"
        ] = limit

        captured[
            "center_coordinates"
        ] = (
            center_coordinates
        )

        return []

    monkeypatch.setattr(
        graph_nodes,
        "search_places",
        fake_search_places,
    )

    state = {
        "request": request,
        "venues": [],
        "plans": [],
        "searched_categories": [],
        "search_count": 0,
        "start_coordinates": (
            42.3507,
            -71.0797,
        ),
    }

    graph_nodes.search_venues_node(
        state
    )

    assert (
        captured[
            "city"
        ]
        == "Boston"
    )

    assert (
        captured[
            "center_coordinates"
        ]
        == (
            42.3507,
            -71.0797,
        )
    )

    assert (
        captured[
            "limit"
        ]
        == 10
    )
