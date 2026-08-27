from __future__ import annotations

import os
from dataclasses import (
    dataclass,
)


def parse_bool(
    value: str | None,
    *,
    default: bool = False,
) -> bool:
    """
    Convert a common environment-variable string into a boolean.
    """

    if value is None:
        return default

    normalized = (
        value
        .strip()
        .lower()
    )

    return normalized in {
        "1",
        "true",
        "yes",
        "on",
    }


def parse_origins(
    value: str | None,
) -> list[str]:
    """
    Parse comma-separated CORS origins.

    Example:

        https://planpilot.streamlit.app,
        http://localhost:8501
    """

    if not value:
        return [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
        ]

    return [
        origin.strip().rstrip("/")
        for origin
        in value.split(",")
        if origin.strip()
    ]


@dataclass(
    frozen=True
)
class AppSettings:
    """
    Runtime configuration for PlanPilot.

    All production-specific values come from environment variables
    rather than being hardcoded into application code.
    """

    environment: str

    host: str

    port: int

    cors_origins: list[str]

    docs_enabled: bool

    debug: bool

    @property
    def is_production(
        self,
    ) -> bool:
        return (
            self.environment
            == "production"
        )


def load_settings() -> AppSettings:
    """
    Load PlanPilot runtime settings from the environment.
    """

    environment = (
        os.getenv(
            "PLANPILOT_ENV",
            "development",
        )
        .strip()
        .lower()
    )

    port_value = (
        os.getenv(
            "PORT",
            "8000",
        )
    )

    try:
        port = int(
            port_value
        )

    except ValueError:
        port = 8000

    return AppSettings(
        environment=environment,
        host=os.getenv(
            "HOST",
            "0.0.0.0",
        ),
        port=port,
        cors_origins=parse_origins(
            os.getenv(
                "CORS_ORIGINS"
            )
        ),
        docs_enabled=parse_bool(
            os.getenv(
                "DOCS_ENABLED"
            ),
            default=(
                environment
                != "production"
            ),
        ),
        debug=parse_bool(
            os.getenv(
                "DEBUG"
            ),
            default=False,
        ),
    )


SETTINGS = (
    load_settings()
)
