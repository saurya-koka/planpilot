from __future__ import annotations

from fastapi.testclient import (
    TestClient,
)

from backend.app.config import (
    SETTINGS,
)
from backend.app.main import (
    app,
)


client = TestClient(
    app
)


def test_health_exposes_environment() -> None:
    response = client.get(
        "/health"
    )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        "environment"
        in payload
    )

    assert (
        payload[
            "environment"
        ]
        == SETTINGS.environment
    )

    assert (
        "docs_enabled"
        in payload
    )

    assert (
        payload[
            "docs_enabled"
        ]
        == SETTINGS.docs_enabled
    )


def test_cors_preflight_local_frontend() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": (
                "http://localhost:8501"
            ),
            "Access-Control-Request-Method": (
                "GET"
            ),
        },
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.headers[
            "access-control-allow-origin"
        ]
        == "http://localhost:8501"
    )
