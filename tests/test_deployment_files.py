from __future__ import annotations

from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


def test_render_blueprint_exists() -> None:
    path = (
        ROOT
        / "render.yaml"
    )

    assert path.exists()


def test_render_blueprint_has_fastapi_start_command() -> None:
    content = (
        ROOT
        / "render.yaml"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "uvicorn backend.app.main:app"
        in content
    )

    assert (
        "--port $PORT"
        in content
    )


def test_render_blueprint_has_health_check() -> None:
    content = (
        ROOT
        / "render.yaml"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "healthCheckPath: /health"
        in content
    )


def test_render_blueprint_uses_secret_placeholders() -> None:
    content = (
        ROOT
        / "render.yaml"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "OPENAI_API_KEY"
        in content
    )

    assert (
        "GEOAPIFY_API_KEY"
        in content
    )

    assert (
        "sync: false"
        in content
    )


def test_streamlit_config_exists() -> None:
    path = (
        ROOT
        / ".streamlit"
        / "config.toml"
    )

    assert path.exists()


def test_streamlit_config_is_headless() -> None:
    content = (
        ROOT
        / ".streamlit"
        / "config.toml"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "headless = true"
        in content
    )
