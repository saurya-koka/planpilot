from __future__ import annotations

from backend.app.config import (
    load_settings,
    parse_bool,
    parse_origins,
)


def test_parse_bool_true_values() -> None:
    assert (
        parse_bool(
            "true"
        )
        is True
    )

    assert (
        parse_bool(
            "1"
        )
        is True
    )

    assert (
        parse_bool(
            "yes"
        )
        is True
    )


def test_parse_bool_false_values() -> None:
    assert (
        parse_bool(
            "false"
        )
        is False
    )

    assert (
        parse_bool(
            "0"
        )
        is False
    )


def test_parse_bool_default() -> None:
    assert (
        parse_bool(
            None,
            default=True,
        )
        is True
    )


def test_parse_origins_defaults() -> None:
    origins = (
        parse_origins(
            None
        )
    )

    assert (
        "http://localhost:8501"
        in origins
    )

    assert (
        "http://127.0.0.1:8501"
        in origins
    )


def test_parse_origins_from_environment() -> None:
    origins = (
        parse_origins(
            (
                "https://planpilot.example.com,"
                "http://localhost:8501"
            )
        )
    )

    assert origins == [
        "https://planpilot.example.com",
        "http://localhost:8501",
    ]


def test_load_settings_production(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "PLANPILOT_ENV",
        "production",
    )

    monkeypatch.setenv(
        "PORT",
        "9000",
    )

    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://planpilot.example.com",
    )

    monkeypatch.setenv(
        "DOCS_ENABLED",
        "false",
    )

    settings = (
        load_settings()
    )

    assert (
        settings.environment
        == "production"
    )

    assert (
        settings.is_production
        is True
    )

    assert (
        settings.port
        == 9000
    )

    assert settings.cors_origins == [
        "https://planpilot.example.com"
    ]

    assert (
        settings.docs_enabled
        is False
    )


def test_invalid_port_uses_default(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "PORT",
        "not-a-number",
    )

    settings = (
        load_settings()
    )

    assert (
        settings.port
        == 8000
    )
