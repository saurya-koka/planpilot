from __future__ import annotations

import os
import re
from datetime import time
from html import escape
from textwrap import dedent
from typing import Any

import pydeck as pdk
import requests
import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="PlanPilot | AI Planning Command Center",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()


def get_backend_url() -> str:
    try:
        secret_backend_url = st.secrets.get("BACKEND_URL")
        if secret_backend_url:
            return str(secret_backend_url).strip().rstrip("/")
    except Exception:
        pass

    return os.getenv("BACKEND_URL", "http://localhost:8000").strip().rstrip("/")


BACKEND_URL = get_backend_url()
IS_LOCAL = BACKEND_URL.startswith(
    ("http://localhost", "http://127.0.0.1")
)
ENVIRONMENT_LABEL = (
    "Local development"
    if IS_LOCAL
    else "Production deployment"
)
ENVIRONMENT_STATUS = (
    "Development mode"
    if IS_LOCAL
    else "Production mode"
)


def render_html(html: str) -> None:
    """Render custom HTML without Markdown treating indentation as code."""
    st.markdown(dedent(html).strip(), unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Visual system
# -----------------------------------------------------------------------------

render_html(
    """
    <style>
    :root {
        --pp-bg: #06101d;
        --pp-bg-soft: #0a1626;
        --pp-panel: rgba(12, 29, 48, 0.82);
        --pp-border: rgba(85, 196, 255, 0.17);
        --pp-cyan: #28e6e0;
        --pp-blue: #3b82f6;
        --pp-violet: #8b5cf6;
        --pp-green: #31e6a1;
        --pp-amber: #f6c75b;
        --pp-text: #eef7ff;
        --pp-muted: #8297ad;
    }

    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, system-ui, -apple-system,
            BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 18% 8%, rgba(32,193,255,.08), transparent 26%),
            radial-gradient(circle at 82% 18%, rgba(108,92,231,.08), transparent 28%),
            linear-gradient(180deg, #06101d 0%, #07131f 52%, #05101a 100%);
        color: var(--pp-text);
    }

    .block-container {
        max-width: 1520px;
        padding: 1.3rem 2rem 5rem;
    }

    #MainMenu, footer { visibility: hidden; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(5,18,32,.99), rgba(5,14,26,.98));
        border-right: 1px solid rgba(85,196,255,.12);
    }

    .pp-side-brand { padding: 1rem .75rem 1.25rem; }
    .pp-side-logo {
        font-size: 1.45rem;
        font-weight: 850;
        color: #fff;
        display: flex;
        gap: .6rem;
        align-items: center;
    }
    .pp-side-logo-mark {
        color: var(--pp-cyan);
        text-shadow: 0 0 14px rgba(40,230,224,.42);
    }
    .pp-side-sub { color: var(--pp-muted); font-size: .78rem; margin-top: .3rem; }
    .pp-side-section {
        color: #60758a;
        font-size: .68rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .12em;
        margin: 1.25rem .75rem .45rem;
    }
    .pp-nav-item {
        border-radius: 10px;
        padding: .68rem .78rem;
        margin: .18rem .25rem;
        color: #9eb1c3;
        border: 1px solid transparent;
        font-size: .86rem;
    }
    .pp-nav-item-active {
        color: #eaffff;
        background: linear-gradient(90deg, rgba(24,185,203,.16), rgba(19,129,170,.05));
        border-color: rgba(40,230,224,.17);
        box-shadow: inset 3px 0 0 rgba(40,230,224,.8);
    }
    .pp-capability-row {
        display: flex;
        align-items: center;
        gap: .55rem;
        padding: .5rem .75rem;
        margin: .08rem .25rem;
        color: #8ea4b8;
        font-size: .8rem;
    }
    .pp-capability-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: rgba(40,230,224,.88);
        box-shadow: 0 0 8px rgba(40,230,224,.28);
        flex: 0 0 auto;
    }
    .pp-side-status {
        margin: 1.7rem .35rem 0;
        padding: .85rem;
        border-radius: 14px;
        border: 1px solid rgba(49,230,161,.16);
        background: rgba(49,230,161,.045);
    }
    .pp-side-status-title { color: #8ca1b5; font-size: .72rem; }
    .pp-side-status-live { color: var(--pp-green); font-size: .82rem; font-weight: 750; margin-top: .28rem; }

    .pp-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: .6rem .2rem 1.2rem;
    }
    .pp-header-label {
        color: var(--pp-muted);
        font-size: .82rem;
        text-transform: uppercase;
        letter-spacing: .09em;
        font-weight: 700;
    }
    .pp-system-state {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .35rem .7rem;
        border-radius: 999px;
        border: 1px solid rgba(49,230,161,.22);
        color: #87f3c3;
        background: rgba(49,230,161,.055);
        font-size: .73rem;
        font-weight: 750;
    }
    .pp-system-dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--pp-green);
        box-shadow: 0 0 10px rgba(49,230,161,.75);
    }

    .pp-hero {
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(55,201,239,.16);
        border-radius: 22px;
        padding: 1.8rem 2rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, rgba(12,34,56,.92), rgba(8,25,44,.88));
        box-shadow: 0 20px 55px rgba(0,0,0,.18);
    }
    .pp-hero::after {
        content: "";
        position: absolute;
        width: 420px; height: 420px;
        right: -180px; top: -220px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(31,194,239,.12), transparent 68%);
        pointer-events: none;
    }
    .pp-kicker {
        color: var(--pp-cyan);
        font-size: .76rem;
        text-transform: uppercase;
        letter-spacing: .14em;
        font-weight: 800;
        margin-bottom: .65rem;
    }
    .pp-hero-title {
        font-size: clamp(2.1rem, 3.4vw, 3.4rem);
        font-weight: 850;
        line-height: 1.03;
        margin: 0 0 .7rem;
        color: #f6fbff;
    }
    .pp-gradient-text {
        background: linear-gradient(90deg, #53efe7, #54a8ff, #9b73ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .pp-hero-copy { max-width: 760px; color: #91a6ba; font-size: 1rem; line-height: 1.65; }
    .pp-pills { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1.15rem; }
    .pp-pill {
        display: inline-flex;
        align-items: center;
        gap: .42rem;
        padding: .45rem .7rem;
        border-radius: 999px;
        color: #b5c8da;
        border: 1px solid rgba(100,180,215,.16);
        background: rgba(4,17,30,.38);
        font-size: .74rem;
        font-weight: 650;
    }
    .pp-pill-dot {
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--pp-green);
        box-shadow: 0 0 8px rgba(49,230,161,.6);
    }

    div[data-baseweb="textarea"] textarea,
    div[data-baseweb="input"] input {
        background: rgba(5,17,30,.72) !important;
        border-color: rgba(60,182,220,.17) !important;
        color: #eef7ff !important;
        border-radius: 12px !important;
    }
    div[data-baseweb="select"] > div {
        background: rgba(5,17,30,.72) !important;
        border-color: rgba(60,182,220,.17) !important;
    }
    label[data-testid="stWidgetLabel"] p { color: #9fb3c6 !important; font-size: .78rem !important; }

    div.stButton > button[kind="primary"] {
        border: 0 !important;
        border-radius: 12px !important;
        color: #00151c !important;
        font-weight: 850 !important;
        background: linear-gradient(90deg, #25e0d8, #3ec5ed) !important;
        box-shadow: 0 10px 32px rgba(21,203,212,.18);
        transition: transform 160ms ease, filter 160ms ease, box-shadow 160ms ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        filter: brightness(1.06);
        box-shadow: 0 14px 38px rgba(21,203,212,.28);
    }
    div.stButton > button { border-radius: 10px; }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(88,186,222,.12);
        background: rgba(8,24,40,.65);
        padding: .85rem;
        border-radius: 14px;
    }
    div[data-testid="stMetricLabel"] { color: #7890a6; }
    div[data-testid="stMetricValue"] { color: #f4fbff; }

    .pp-weather {
        position: relative;
        overflow: hidden;
        min-height: 245px;
        border-radius: 18px;
        padding: 1.15rem;
        border: 1px solid rgba(66,197,224,.18);
        background: linear-gradient(145deg, rgba(12,37,59,.93), rgba(11,28,46,.9));
    }
    .pp-weather-city { color: #eaf7ff; font-weight: 760; font-size: .9rem; }
    .pp-weather-source { color: #607a91; font-size: .7rem; }
    .pp-weather-main { display: flex; align-items: center; gap: .8rem; margin-top: 1.1rem; }
    .pp-weather-icon { font-size: 2.5rem; }
    .pp-weather-temp { font-size: 2.2rem; font-weight: 800; color: #f4fbff; }
    .pp-weather-condition { color: #91a8bb; margin-top: .05rem; font-size: .82rem; }
    .pp-weather-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: .5rem; margin-top: 1.25rem; }
    .pp-weather-stat {
        border: 1px solid rgba(106,177,203,.1);
        background: rgba(5,17,29,.33);
        border-radius: 10px;
        padding: .58rem;
    }
    .pp-weather-stat-label { color: #5f7890; font-size: .65rem; }
    .pp-weather-stat-value { color: #dcecf7; font-size: .8rem; font-weight: 720; margin-top: .15rem; }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(78,173,209,.13) !important;
        border-radius: 18px !important;
        background: linear-gradient(180deg, rgba(11,28,46,.74), rgba(7,20,35,.7)) !important;
        box-shadow: 0 12px 32px rgba(0,0,0,.11);
    }

    .plan-label,
    .category-badge,
    .source-badge,
    .routing-live-badge,
    .routing-fallback-badge {
        display: inline-block;
        border-radius: 999px;
        font-weight: 730;
        margin-right: .3rem;
    }
    .plan-label { padding: .3rem .65rem; font-size: .7rem; color: #91f3ef; border: 1px solid rgba(40,230,224,.18); background: rgba(40,230,224,.07); margin-bottom: .55rem; }
    .category-badge { padding: .2rem .48rem; font-size: .65rem; color: #aabfd2; border: 1px solid rgba(128,176,208,.15); background: rgba(128,176,208,.05); }
    .source-badge { padding: .2rem .48rem; font-size: .65rem; color: #61e2dd; border: 1px solid rgba(40,230,224,.17); background: rgba(40,230,224,.06); }
    .routing-live-badge { padding: .24rem .55rem; font-size: .68rem; color: #7ceeba; border: 1px solid rgba(49,230,161,.17); background: rgba(49,230,161,.07); }
    .routing-fallback-badge { padding: .24rem .55rem; font-size: .68rem; color: #e6c474; border: 1px solid rgba(246,199,91,.17); background: rgba(246,199,91,.07); }

    .stop-card {
        padding: .9rem 1rem;
        margin: .55rem 0;
        border-radius: 13px;
        border: 1px solid rgba(91,174,205,.12);
        background: rgba(7,21,36,.5);
        transition: border-color 160ms ease, transform 160ms ease, background 160ms ease;
    }
    .stop-card:hover { border-color: rgba(55,217,226,.24); transform: translateY(-1px); background: rgba(9,27,45,.68); }
    .stop-title { font-size: 1rem; font-weight: 780; color: #eff9ff; margin: .45rem 0 .28rem; }
    .stop-details { color: #829ab0; font-size: .82rem; line-height: 1.55; }
    .timeline-arrow { color: rgba(68,214,220,.72); text-align: center; font-size: 1.1rem; margin: .05rem 0; }
    .route-leg {
        padding: .65rem .75rem;
        border-radius: 10px;
        border: 1px solid rgba(90,170,200,.11);
        background: rgba(7,20,33,.42);
        margin-bottom: .4rem;
        color: #93a9bb;
        font-size: .8rem;
    }
    .notice-box {
        border: 1px solid rgba(55,204,220,.14);
        background: rgba(20,152,177,.055);
        border-radius: 14px;
        padding: .8rem .9rem;
        color: #9db2c3;
        font-size: .78rem;
        margin-bottom: 1rem;
    }

    .pp-agent-panel {
        margin-top: 1rem;
        border: 1px solid rgba(83,176,211,.13);
        border-radius: 16px;
        background: rgba(8,23,39,.62);
        padding: .9rem 1rem;
    }
    .pp-agent-title { color: #dbeaf5; font-size: .78rem; font-weight: 750; margin-bottom: .15rem; }
    .pp-agent-subtitle { color: #617b91; font-size: .65rem; margin-bottom: .7rem; }
    .pp-agent-steps { display: flex; align-items: center; justify-content: space-between; gap: .35rem; overflow-x: auto; }
    .pp-agent-step { min-width: 82px; text-align: center; }
    .pp-agent-node {
        width: 28px; height: 28px; margin: auto; display: flex; align-items: center; justify-content: center;
        border-radius: 50%; color: #06141c; background: linear-gradient(135deg,#41e6df,#42aaf6);
        box-shadow: 0 0 13px rgba(40,230,224,.18); font-size: .7rem; font-weight: 850;
    }
    .pp-agent-step-label { color: #8197aa; font-size: .62rem; margin-top: .35rem; }
    .pp-agent-line { height: 1px; flex: 1; min-width: 20px; background: linear-gradient(90deg, rgba(40,230,224,.65), rgba(80,122,255,.32)); }

    .pp-suggestion {
        border: 1px solid rgba(76,169,204,.13);
        background: linear-gradient(180deg, rgba(11,28,46,.69), rgba(7,20,34,.61));
        border-radius: 14px;
        padding: .85rem;
        min-height: 158px;
        transition: transform 170ms ease, border-color 170ms ease, box-shadow 170ms ease;
    }
    .pp-suggestion:hover { transform: translateY(-3px); border-color: rgba(40,230,224,.26); box-shadow: 0 14px 30px rgba(0,0,0,.14); }
    .pp-suggestion-icon { font-size: 1.2rem; }
    .pp-suggestion-name { color: #eef8ff; font-weight: 760; font-size: .93rem; margin-top: .48rem; }
    .pp-suggestion-meta { color: #73899e; font-size: .72rem; line-height: 1.5; margin-top: .35rem; }
    .pp-suggestion-reason {
        color: #60d9d6;
        font-size: .68rem;
        margin-top: .65rem;
        padding-top: .55rem;
        border-top: 1px solid rgba(76,169,204,.10);
    }

    button[data-baseweb="tab"] { color: #8499ac !important; font-size: .78rem !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #52dfda !important; }
    details { background: rgba(8,23,38,.42) !important; border-radius: 12px !important; border: 1px solid rgba(73,158,192,.1) !important; }

    @media (max-width: 900px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .pp-agent-steps { justify-content: flex-start; }
        .pp-hero { padding: 1.4rem; }
    }
    </style>
    """
)

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------

with st.sidebar:
    render_html(
        f"""
        <div class="pp-side-brand">
            <div class="pp-side-logo">
                <span class="pp-side-logo-mark">◈</span>
                PlanPilot
            </div>
            <div class="pp-side-sub">
                Agentic planning for real life.
            </div>
        </div>

        <div class="pp-side-section">Workspace</div>
        <div class="pp-nav-item pp-nav-item-active">
            ◉ &nbsp; Command Center
        </div>

        <div class="pp-side-section">Intelligence stack</div>

        <div class="pp-capability-row">
            <span class="pp-capability-dot"></span>
            Live place discovery
        </div>

        <div class="pp-capability-row">
            <span class="pp-capability-dot"></span>
            Weather-aware planning
        </div>

        <div class="pp-capability-row">
            <span class="pp-capability-dot"></span>
            Hybrid RAG + reranking
        </div>

        <div class="pp-capability-row">
            <span class="pp-capability-dot"></span>
            Constraint validation
        </div>

        <div class="pp-side-section">Engineering</div>

        <div class="pp-capability-row">
            <span class="pp-capability-dot"></span>
            Evaluation framework
        </div>

        <div class="pp-capability-row">
            <span class="pp-capability-dot"></span>
            Structured observability
        </div>
        """
    )

    render_html(
        f'<div class="pp-side-status"><div class="pp-side-status-title">{escape(ENVIRONMENT_LABEL)}</div><div class="pp-side-status-live">● {escape(ENVIRONMENT_STATUS)}</div></div>'
    )

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def category_icon(category: str) -> str:
    return {"activity": "🎟️", "restaurant": "🍽️", "dessert": "🍨"}.get(
        category.lower(), "📍"
    )


def transport_icon(mode: str) -> str:
    return {"walking": "🚶", "driving": "🚗", "public_transit": "🚇"}.get(mode, "🧭")


def format_duration(minutes: int | float) -> str:
    total_minutes = int(minutes)
    hours, remaining_minutes = divmod(total_minutes, 60)
    if hours and remaining_minutes:
        return f"{hours}h {remaining_minutes}m"
    if hours:
        return f"{hours}h"
    return f"{remaining_minutes}m"


def format_distance(distance_meters: int | float) -> str:
    meters = float(distance_meters)
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{int(meters)} m"


def extract_schedule(reasons: list[str]) -> dict[str, str]:
    schedule_reason = next(
        (reason for reason in reasons if reason.startswith("Estimated schedule:")), None
    )
    if not schedule_reason:
        return {}

    schedule_text = schedule_reason.removeprefix("Estimated schedule:").strip().rstrip(".")
    schedule: dict[str, str] = {}
    for segment in schedule_text.split("→"):
        match = re.match(r"(.+?)\s+at\s+(\d{1,2}:\d{2}\s+[AP]M)$", segment.strip())
        if match:
            schedule[match.group(1).strip()] = match.group(2).strip()
    return schedule


def request_json(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{BACKEND_URL}{endpoint}", json=payload, timeout=180)
    response.raise_for_status()
    result = response.json()
    if not isinstance(result, dict):
        raise ValueError("The backend returned an unexpected response.")
    return result

# -----------------------------------------------------------------------------
# Weather
# -----------------------------------------------------------------------------


def weather_code_to_info(code: int) -> tuple[str, str]:
    if code == 0:
        return "☀️", "Clear skies"
    if code in {1, 2}:
        return "🌤️", "Partly cloudy"
    if code == 3:
        return "☁️", "Overcast"
    if code in {45, 48}:
        return "🌫️", "Foggy"
    if code in {51, 53, 55, 56, 57}:
        return "🌦️", "Drizzle"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "🌧️", "Rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "❄️", "Snow"
    if code in {95, 96, 99}:
        return "⛈️", "Thunderstorms"
    return "🌤️", "Weather available"


@st.cache_data(ttl=600, show_spinner=False)
def fetch_current_weather(latitude: float, longitude: float) -> dict[str, Any] | None:
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,apparent_temperature,precipitation,"
                    "weather_code,wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=12,
        )
        response.raise_for_status()
        current = response.json().get("current")
        return current if isinstance(current, dict) else None
    except (requests.RequestException, ValueError):
        return None


def get_result_city(result: dict[str, Any]) -> str:
    for key in ("planning_request", "parsed_request"):
        value = result.get(key)
        if isinstance(value, dict) and value.get("city"):
            return str(value["city"])
    return "Current location"


def render_weather_panel(result: dict[str, Any] | None) -> None:
    if not result:
        render_html(
            """
            <div class="pp-weather">
                <div class="pp-weather-city">Weather Today</div>
                <div class="pp-weather-source">Weather-aware planning</div>
                <div class="pp-weather-main">
                    <div class="pp-weather-icon">⛅</div>
                    <div class="pp-weather-condition">
                        Generate a plan to load live conditions for the starting area.
                    </div>
                </div>
                <div class="pp-weather-grid">
                    <div class="pp-weather-stat">
                        <div class="pp-weather-stat-label">Source</div>
                        <div class="pp-weather-stat-value">Open-Meteo</div>
                    </div>
                    <div class="pp-weather-stat">
                        <div class="pp-weather-stat-label">Planner</div>
                        <div class="pp-weather-stat-value">Weather-aware</div>
                    </div>
                    <div class="pp-weather-stat">
                        <div class="pp-weather-stat-label">Status</div>
                        <div class="pp-weather-stat-value">Ready</div>
                    </div>
                </div>
            </div>
            """
        )
        return

    start_coordinates = result.get("start_coordinates")
    if not isinstance(start_coordinates, dict):
        render_html(
            """
            <div class="pp-weather">
                <div class="pp-weather-city">Weather Today</div>
                <div class="pp-weather-source">Open-Meteo</div>
                <div class="pp-weather-main">
                    <div class="pp-weather-icon">⛅</div>
                    <div class="pp-weather-condition">Starting coordinates are unavailable.</div>
                </div>
            </div>
            """
        )
        return

    latitude = start_coordinates.get("latitude")
    longitude = start_coordinates.get("longitude")
    if latitude is None or longitude is None:
        return

    weather = fetch_current_weather(float(latitude), float(longitude))
    if not weather:
        render_html(
            """
            <div class="pp-weather">
                <div class="pp-weather-city">Weather Today</div>
                <div class="pp-weather-source">Open-Meteo</div>
                <div class="pp-weather-main">
                    <div class="pp-weather-icon">⛅</div>
                    <div class="pp-weather-condition">Live conditions are temporarily unavailable.</div>
                </div>
            </div>
            """
        )
        return

    icon, condition = weather_code_to_info(int(weather.get("weather_code", 0)))
    temperature = float(weather.get("temperature_2m", 0))
    apparent = float(weather.get("apparent_temperature", temperature))
    precipitation = float(weather.get("precipitation", 0))
    wind_speed = float(weather.get("wind_speed_10m", 0))
    city = escape(get_result_city(result))

    render_html(
        f"""
        <div class="pp-weather">
            <div class="pp-weather-city">{city}</div>
            <div class="pp-weather-source">Weather today • Open-Meteo</div>
            <div class="pp-weather-main">
                <div class="pp-weather-icon">{icon}</div>
                <div>
                    <div class="pp-weather-temp">{temperature:.0f}°C</div>
                    <div class="pp-weather-condition">{condition}</div>
                </div>
            </div>
            <div class="pp-weather-grid">
                <div class="pp-weather-stat">
                    <div class="pp-weather-stat-label">Feels like</div>
                    <div class="pp-weather-stat-value">{apparent:.0f}°C</div>
                </div>
                <div class="pp-weather-stat">
                    <div class="pp-weather-stat-label">Rain</div>
                    <div class="pp-weather-stat-value">{precipitation:.1f} mm</div>
                </div>
                <div class="pp-weather-stat">
                    <div class="pp-weather-stat-label">Wind</div>
                    <div class="pp-weather-stat-value">{wind_speed:.0f} km/h</div>
                </div>
            </div>
        </div>
        """
    )

# -----------------------------------------------------------------------------
# Map / route
# -----------------------------------------------------------------------------


def route_geometry_to_path(route_leg: dict[str, Any]) -> list[list[float]]:
    geometry = route_leg.get("geometry", [])
    if not isinstance(geometry, list):
        return []
    path: list[list[float]] = []
    for point in geometry:
        if not isinstance(point, dict):
            continue
        latitude = point.get("latitude")
        longitude = point.get("longitude")
        if latitude is not None and longitude is not None:
            path.append([float(longitude), float(latitude)])
    return path


def calculate_map_zoom(coordinates: list[tuple[float, float]]) -> float:
    if len(coordinates) <= 1:
        return 14.0
    latitudes = [lat for lat, _ in coordinates]
    longitudes = [lon for _, lon in coordinates]
    span = max(max(latitudes) - min(latitudes), max(longitudes) - min(longitudes))
    if span < 0.005:
        return 14.5
    if span < 0.01:
        return 13.8
    if span < 0.025:
        return 12.8
    if span < 0.05:
        return 11.8
    if span < 0.10:
        return 10.8
    return 9.8


def build_map_data(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[tuple[float, float]]]:
    route_legs = list(plan.get("route_legs", []))
    stops = list(plan.get("stops", []))
    route_paths: list[dict[str, Any]] = []
    stop_markers: list[dict[str, Any]] = []
    start_markers: list[dict[str, Any]] = []
    all_coordinates: list[tuple[float, float]] = []

    for leg_index, leg in enumerate(route_legs, start=1):
        path = route_geometry_to_path(leg)
        if len(path) < 2:
            continue
        fallback_used = bool(leg.get("fallback_used", False))
        route_paths.append(
            {
                "path": path,
                "name": f"{leg.get('from_name', 'Start')} → {leg.get('to_name', 'Destination')}",
                "from_name": leg.get("from_name", "Start"),
                "to_name": leg.get("to_name", "Destination"),
                "duration": format_duration(leg.get("duration_minutes", 0)),
                "distance": format_distance(leg.get("distance_meters", 0)),
                "provider": str(leg.get("provider", "unknown")),
                "route_type": "Estimated" if fallback_used else "Live",
            }
        )
        for longitude, latitude in path:
            all_coordinates.append((latitude, longitude))
        if leg_index == 1:
            start_markers.append(
                {
                    "longitude": path[0][0],
                    "latitude": path[0][1],
                    "label": "S",
                    "name": leg.get("from_name", "Starting point"),
                    "category": "Starting point",
                }
            )

    for stop_index, stop in enumerate(stops, start=1):
        latitude = stop.get("latitude")
        longitude = stop.get("longitude")
        if latitude is None or longitude is None:
            continue
        lat = float(latitude)
        lon = float(longitude)
        stop_markers.append(
            {
                "longitude": lon,
                "latitude": lat,
                "label": str(stop_index),
                "name": stop.get("name", f"Stop {stop_index}"),
                "category": str(stop.get("category", "stop")).title(),
                "area": stop.get("area", ""),
            }
        )
        all_coordinates.append((lat, lon))

    return route_paths, stop_markers, start_markers, all_coordinates


def render_plan_map(plan: dict[str, Any], plan_number: int) -> None:
    route_paths, stop_markers, start_markers, all_coordinates = build_map_data(plan)
    if not all_coordinates:
        st.info("Map data is not available for this plan.")
        return

    center_latitude = sum(c[0] for c in all_coordinates) / len(all_coordinates)
    center_longitude = sum(c[1] for c in all_coordinates) / len(all_coordinates)
    layers: list[pdk.Layer] = []

    if route_paths:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=route_paths,
                get_path="path",
                get_width=6,
                get_color=[40, 230, 224],
                width_min_pixels=4,
                pickable=True,
                auto_highlight=True,
            )
        )

    if start_markers:
        layers.extend(
            [
                pdk.Layer(
                    "ScatterplotLayer",
                    data=start_markers,
                    get_position="[longitude, latitude]",
                    get_radius=70,
                    get_fill_color=[46, 220, 157],
                    get_line_color=[235, 255, 250],
                    radius_min_pixels=11,
                    radius_max_pixels=18,
                    pickable=True,
                    stroked=True,
                    filled=True,
                    line_width_min_pixels=2,
                ),
                pdk.Layer(
                    "TextLayer",
                    data=start_markers,
                    get_position="[longitude, latitude]",
                    get_text="label",
                    get_color=[255, 255, 255],
                    get_size=14,
                    size_min_pixels=12,
                    size_max_pixels=18,
                    get_alignment_baseline="'center'",
                    get_text_anchor="'middle'",
                ),
            ]
        )

    if stop_markers:
        layers.extend(
            [
                pdk.Layer(
                    "ScatterplotLayer",
                    data=stop_markers,
                    get_position="[longitude, latitude]",
                    get_radius=75,
                    get_fill_color=[65, 154, 246],
                    get_line_color=[220, 244, 255],
                    radius_min_pixels=11,
                    radius_max_pixels=18,
                    pickable=True,
                    stroked=True,
                    filled=True,
                    line_width_min_pixels=2,
                ),
                pdk.Layer(
                    "TextLayer",
                    data=stop_markers,
                    get_position="[longitude, latitude]",
                    get_text="label",
                    get_color=[255, 255, 255],
                    get_size=15,
                    size_min_pixels=12,
                    size_max_pixels=19,
                    get_alignment_baseline="'center'",
                    get_text_anchor="'middle'",
                ),
            ]
        )

    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=center_latitude,
            longitude=center_longitude,
            zoom=calculate_map_zoom(all_coordinates),
            pitch=0,
            bearing=0,
        ),
        layers=layers,
        tooltip={
            "html": "<b>{name}</b><br/>{category}<br/>{area}{duration}{distance}{provider}",
            "style": {
                "backgroundColor": "#071522",
                "color": "white",
                "border": "1px solid rgba(40,230,224,.25)",
            },
        },
    )
    st.pydeck_chart(deck, use_container_width=True, key=f"plan_map_{plan_number}")


def render_route_summary(route_legs: list[dict[str, Any]]) -> None:
    if not route_legs:
        return
    total_distance = sum(int(leg.get("distance_meters", 0)) for leg in route_legs)
    live_count = sum(1 for leg in route_legs if not bool(leg.get("fallback_used", False)))
    fallback_count = len(route_legs) - live_count
    c1, c2, c3 = st.columns(3)
    c1.metric("Route distance", format_distance(total_distance))
    c2.metric("Live route legs", live_count)
    c3.metric("Fallback legs", fallback_count)

    badges = ""
    if live_count:
        badges += f'<span class="routing-live-badge">● {live_count} live route{"s" if live_count != 1 else ""}</span>'
    if fallback_count:
        badges += f'<span class="routing-fallback-badge">~ {fallback_count} estimated route{"s" if fallback_count != 1 else ""}</span>'
    if badges:
        render_html(badges)

    with st.expander("Route breakdown"):
        for index, leg in enumerate(route_legs, start=1):
            fallback_used = bool(leg.get("fallback_used", False))
            render_html(
                f"""
                <div class="route-leg">
                    <strong>Leg {index}: {leg.get('from_name', 'Start')} → {leg.get('to_name', 'Destination')}</strong><br>
                    {transport_icon(str(leg.get('mode', 'unknown')))}
                    {format_duration(int(leg.get('duration_minutes', 0)))}
                    &nbsp;•&nbsp; 📏 {format_distance(int(leg.get('distance_meters', 0)))}
                    &nbsp;•&nbsp; {'Estimated fallback' if fallback_used else 'Live routing'}
                    &nbsp;•&nbsp; {leg.get('provider', 'unknown')}
                </div>
                """
            )

# -----------------------------------------------------------------------------
# Plan presentation
# -----------------------------------------------------------------------------


def render_stop(stop: dict[str, Any], arrival_time: str | None) -> None:
    category = str(stop.get("category", "stop"))
    name = escape(str(stop.get("name", "Unknown venue")))
    area = escape(str(stop.get("area", "Area unavailable")))
    cost = float(stop.get("estimated_cost", 0))
    duration = int(stop.get("duration_minutes", 0))
    source = str(stop.get("source", "estimated"))
    formatted_address = stop.get("formatted_address")
    opening_hours = stop.get("opening_hours")
    website = stop.get("website")

    badges = (
        f'<span class="category-badge">{category_icon(category)} {category.title()}</span>'
    )
    if source == "geoapify":
        badges += '<span class="source-badge">● Live place data</span>'

    timing_text = f"Arrival: {arrival_time}" if arrival_time else "Arrival time unavailable"
    render_html(
        f"""
        <div class="stop-card">
            <div>{badges}</div>
            <div class="stop-title">{name}</div>
            <div class="stop-details">
                📍 {area}<br>
                🕒 {timing_text} &nbsp;•&nbsp; Stay: {format_duration(duration)}<br>
                💳 Estimated group cost: ${cost:.0f}
            </div>
        </div>
        """
    )

    c1, c2, c3 = st.columns([1.2, 1.2, 0.8])
    with c1:
        st.caption(f"Address: {formatted_address}" if formatted_address else "Address unavailable")
    with c2:
        st.caption(
            f"Hours data: {opening_hours}"
            if opening_hours
            else "Hours not provided by the live source"
        )
    with c3:
        if website:
            st.link_button("Venue ↗", website, use_container_width=True)


def render_agent_pipeline() -> None:
    """
    Show the capabilities available across PlanPilot V2.

    This is intentionally presented as the intelligence stack,
    not as a literal per-request execution trace.
    """

    html = (
        '<div class="pp-agent-panel">'
        '<div class="pp-agent-title">PlanPilot intelligence stack</div>'
        '<div class="pp-agent-subtitle">Capabilities available across the V2 planning system.</div>'
        '<div class="pp-agent-steps">'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">1</div>'
        '<div class="pp-agent-step-label">Intent</div>'
        '</div>'
        '<div class="pp-agent-line"></div>'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">2</div>'
        '<div class="pp-agent-step-label">Weather</div>'
        '</div>'
        '<div class="pp-agent-line"></div>'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">3</div>'
        '<div class="pp-agent-step-label">Live Places</div>'
        '</div>'
        '<div class="pp-agent-line"></div>'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">4</div>'
        '<div class="pp-agent-step-label">Hybrid RAG</div>'
        '</div>'
        '<div class="pp-agent-line"></div>'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">5</div>'
        '<div class="pp-agent-step-label">Planning</div>'
        '</div>'
        '<div class="pp-agent-line"></div>'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">6</div>'
        '<div class="pp-agent-step-label">Routing</div>'
        '</div>'
        '<div class="pp-agent-line"></div>'

        '<div class="pp-agent-step">'
        '<div class="pp-agent-node">7</div>'
        '<div class="pp-agent-step-label">Validation</div>'
        '</div>'

        '</div>'
        '</div>'
    )

    render_html(html)


def build_suggested_places(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not plans:
        return []
    selected_names = {
        str(stop.get("name", "")).strip().lower()
        for stop in plans[0].get("stops", [])
        if isinstance(stop, dict)
    }
    suggestions: list[dict[str, Any]] = []
    seen_names = set(selected_names)
    for plan in plans[1:]:
        for stop in plan.get("stops", []):
            if not isinstance(stop, dict):
                continue
            name = str(stop.get("name", "")).strip()
            normalized = name.lower()
            if not name or normalized in seen_names:
                continue
            seen_names.add(normalized)
            suggestions.append(stop)
            if len(suggestions) >= 6:
                return suggestions
    return suggestions


def _suggestion_reason(
    suggestion: dict[str, Any],
    selected_plan: dict[str, Any],
) -> str:
    category = str(
        suggestion.get(
            "category",
            "place",
        )
    ).lower()

    suggestion_cost = float(
        suggestion.get(
            "estimated_cost",
            0,
        )
    )

    selected_same_category = next(
        (
            stop
            for stop in selected_plan.get(
                "stops",
                [],
            )
            if isinstance(stop, dict)
            and str(
                stop.get(
                    "category",
                    "",
                )
            ).lower()
            == category
        ),
        None,
    )

    if isinstance(
        selected_same_category,
        dict,
    ):
        selected_cost = float(
            selected_same_category.get(
                "estimated_cost",
                0,
            )
        )

        if (
            suggestion_cost > 0
            and selected_cost > 0
            and suggestion_cost
            < selected_cost
        ):
            return (
                "Lower-cost "
                f"{category} alternative"
            )

    area = str(
        suggestion.get(
            "area",
            "",
        )
    ).strip()

    if area:
        return (
            f"Alternative {category} "
            f"in {area}"
        )

    return (
        f"Alternate {category} "
        "from another ranked plan"
    )


def render_suggested_places(
    plans: list[dict[str, Any]],
) -> None:
    suggestions = build_suggested_places(
        plans
    )

    if not suggestions:
        return

    selected_plan = plans[0]

    st.markdown(
        "## Suggested places"
    )

    st.caption(
        "Real alternatives surfaced by other ranked PlanPilot options."
    )

    columns = st.columns(
        min(
            3,
            len(
                suggestions
            ),
        )
    )

    for (
        index,
        suggestion,
    ) in enumerate(
        suggestions
    ):
        column = columns[
            index
            % len(
                columns
            )
        ]

        name = escape(
            str(
                suggestion.get(
                    "name",
                    "Alternative venue",
                )
            )
        )

        category_raw = str(
            suggestion.get(
                "category",
                "place",
            )
        )

        category = escape(
            category_raw
        )

        area = escape(
            str(
                suggestion.get(
                    "area",
                    "Area unavailable",
                )
            )
        )

        cost = float(
            suggestion.get(
                "estimated_cost",
                0,
            )
        )

        source = str(
            suggestion.get(
                "source",
                "estimated",
            )
        )

        source_label = (
            "Live place data"
            if source
            == "geoapify"
            else "Planner candidate"
        )

        reason = escape(
            _suggestion_reason(
                suggestion,
                selected_plan,
            )
        )

        icon = category_icon(
            category_raw
        )

        card_html = (
            '<div class="pp-suggestion">'
            f'<div class="pp-suggestion-icon">{icon}</div>'
            f'<div class="pp-suggestion-name">{name}</div>'
            f'<div class="pp-suggestion-meta">{category.title()}<br>📍 {area}<br>💳 Est. ${cost:.0f}</div>'
            f'<div class="pp-suggestion-reason"><strong>Why suggested:</strong> {reason}<br>{escape(source_label)}</div>'
            '</div>'
        )

        with column:
            render_html(
                card_html
            )


def render_plan(plan: dict[str, Any], plan_number: int) -> None:
    label = str(plan.get("label", f"Option {plan_number}"))
    title = str(plan.get("title", "Plan option"))
    total_cost = float(plan.get("total_cost", 0))
    travel_minutes = int(plan.get("estimated_travel_minutes", 0))
    total_duration = int(plan.get("total_duration_minutes", 0))
    reasons = list(plan.get("reasons", []))
    warnings = list(plan.get("warnings", []))
    stops = list(plan.get("stops", []))
    route_legs = list(plan.get("route_legs", []))
    schedule = extract_schedule(reasons)

    with st.container(border=True):
        render_html(f'<span class="plan-label">◈ {label}</span>')
        st.subheader(title)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Estimated total", f"${total_cost:.0f}")
        m2.metric("Travel time", format_duration(travel_minutes))
        m3.metric("Full outing", format_duration(total_duration))
        m4.metric("Stops", len(stops))

        if warnings:
            with st.expander(f"⚠ {len(warnings)} planning notes"):
                for warning in warnings:
                    st.warning(warning)
        else:
            st.success("Plan passed current availability, budget and travel checks.", icon="✓")

        itinerary_col, map_col = st.columns([0.88, 1.35], gap="large")
        with itinerary_col:
            st.markdown("### Itinerary")
            for stop_index, stop in enumerate(stops):
                render_stop(stop, schedule.get(str(stop.get("name", ""))))
                if stop_index < len(stops) - 1:
                    render_html('<div class="timeline-arrow">↓</div>')

        with map_col:
            st.markdown("### Route map")
            if route_legs:
                render_plan_map(plan, plan_number)
                render_route_summary(route_legs)
            else:
                st.info("Route information is not available for this plan.")

        with st.expander("Why PlanPilot selected this option"):
            for reason in [r for r in reasons if not r.startswith("Estimated schedule:")]:
                st.write(f"• {reason}")


def render_plans(result: dict[str, Any]) -> None:
    data_notice = result.get("data_notice")
    if data_notice:
        data_notice = escape(str(data_notice))
        render_html(
            f"""
            <div class="notice-box">
                <strong>Live-data notice</strong><br>{data_notice}
            </div>
            """
        )

    plans = list(result.get("plans", []))
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Place data", "Live" if bool(result.get("used_live_data", False)) else "Fallback")
    s2.metric("Candidates checked", result.get("venue_candidate_count") if result.get("venue_candidate_count") is not None else "—")
    s3.metric("Starting point", "Located" if result.get("start_coordinates") else "Unavailable")
    s4.metric("Ranked plans", len(plans))

    render_agent_pipeline()

    with st.expander("What PlanPilot understood"):
        if result.get("parsed_request"):
            st.markdown("**Natural-language interpretation**")
            st.json(result["parsed_request"])
        if result.get("planning_request"):
            st.markdown("**Final planning constraints**")
            st.json(result["planning_request"])

    if not plans:
        st.warning("No viable plans matched all current constraints. Try increasing the budget, travel limit or start time.")
        return

    st.markdown("## Recommended plans")
    tabs = st.tabs([str(plan.get("label", f"Option {index}")) for index, plan in enumerate(plans, start=1)])
    for index, (tab, plan) in enumerate(zip(tabs, plans, strict=True), start=1):
        with tab:
            render_plan(plan, index)

    render_suggested_places(plans)

    if result.get("llm_explanation"):
        st.markdown("## AI reasoning")

        with st.expander(
            "Why these plans were recommended",
            expanded=False,
        ):
            st.markdown(
                str(
                    result[
                        "llm_explanation"
                    ]
                )
            )

# -----------------------------------------------------------------------------
# Session helpers
# -----------------------------------------------------------------------------


def save_result(result: dict[str, Any]) -> None:
    st.session_state["planpilot_result"] = result


def get_saved_result() -> dict[str, Any] | None:
    result = st.session_state.get("planpilot_result")
    return result if isinstance(result, dict) else None

# -----------------------------------------------------------------------------
# Header / command center
# -----------------------------------------------------------------------------

render_html(
    f'<div class="pp-topbar"><div class="pp-header-label">PlanPilot / Command Center</div><div class="pp-system-state"><span class="pp-system-dot"></span>{escape(ENVIRONMENT_LABEL)}</div></div>'
)

render_html(
    """
    <div class="pp-hero">
        <div class="pp-kicker">Agentic AI Planning System</div>
        <div class="pp-hero-title">
            Where to <span class="pp-gradient-text">next?</span>
        </div>
        <div class="pp-hero-copy">
            Describe the outing naturally. PlanPilot combines live places,
            weather-aware planning, hybrid retrieval, routing and deterministic
            validation to build the plan.
        </div>
        <div class="pp-pills">
            <div class="pp-pill"><span class="pp-pill-dot"></span>Agentic Planning</div>
            <div class="pp-pill"><span class="pp-pill-dot"></span>Live Places</div>
            <div class="pp-pill"><span class="pp-pill-dot"></span>Weather-Aware</div>
            <div class="pp-pill"><span class="pp-pill-dot"></span>Hybrid RAG</div>
            <div class="pp-pill"><span class="pp-pill-dot"></span>Constraint Validation</div>
        </div>
    </div>
    """
)

saved_result = get_saved_result()
command_column, weather_column = st.columns([2.65, 1], gap="large")

with command_column:
    with st.container(border=True):
        st.markdown("### Plan with one message")
        st.caption("Tell PlanPilot what you want. Constraints will be extracted automatically.")
        natural_language_request = st.text_area(
            "Describe the outing",
            placeholder=(
                "Plan a chill rainy-day outing in Boston for two people under $150 "
                "with an activity, dinner and dessert."
            ),
            height=126,
        )
        natural_col1, natural_col2 = st.columns(2)
        with natural_col1:
            natural_start_area = st.text_input(
                "Starting area", value="Davis Square", key="natural_start_area"
            )
        with natural_col2:
            natural_food_preferences = st.multiselect(
                "Food preferences",
                [
                    "chicken options", "risotto", "vegetarian", "vegan", "seafood",
                    "Indian", "Chinese", "Thai", "Mexican",
                ],
                default=[],
                key="natural_food_preferences",
            )
        generate_live_plans = st.button(
            "✦ Generate Plan", type="primary", use_container_width=True
        )

with weather_column:
    render_weather_panel(saved_result)

if generate_live_plans:
    if not natural_language_request.strip():
        st.warning("Describe the outing first.")
    elif not natural_start_area.strip():
        st.warning("Enter a starting area.")
    else:
        payload = {
            "text": natural_language_request.strip(),
            "start_area": natural_start_area.strip(),
            "food_preferences": natural_food_preferences,
        }
        try:
            with st.spinner(
                "PlanPilot is searching live places, checking constraints and building ranked itineraries..."
            ):
                result = request_json("/plan-from-text/live/", payload)
        except requests.Timeout:
            st.error("The request took too long. The free production backend may still be waking up.")
        except requests.ConnectionError:
            st.error(f"PlanPilot could not connect to the backend at {BACKEND_URL}.")
        except requests.HTTPError as exc:
            st.error("The backend rejected the request.")
            if exc.response is not None and exc.response.text:
                st.code(exc.response.text)
        except (requests.RequestException, ValueError) as exc:
            st.error(f"Could not generate plans: {exc}")
        else:
            save_result(result)
            st.success("PlanPilot finished the planning run.")
            st.rerun()

saved_result = get_saved_result()
if saved_result:
    st.divider()
    render_plans(saved_result)

# -----------------------------------------------------------------------------
# Manual planner
# -----------------------------------------------------------------------------

st.divider()
with st.expander("Advanced manual planner"):
    with st.form("plan_form"):
        col1, col2 = st.columns(2)
        with col1:
            city = st.text_input("City", "Boston")
            start_area = st.text_input("Starting area", "Davis Square", key="manual_start_area")
            date = st.text_input("Date or weekday", "Friday")
            start_time = st.time_input("Start time", value=time(17, 0))
            budget = st.number_input("Total budget ($)", min_value=20.0, value=200.0, step=10.0)
        with col2:
            party_size = st.number_input("People", min_value=1, max_value=12, value=2)
            transport = st.selectbox("Transport", ["public_transit", "walking", "driving"])
            vibe = st.multiselect(
                "Vibe",
                [
                    "romantic", "fun", "chill", "scenic", "cozy", "stylish", "active",
                    "cultural", "nightlife", "family", "foodie", "budget", "rainy-day",
                    "work-friendly", "group",
                ],
                default=["romantic", "fun"],
            )
            food = st.multiselect(
                "Food preferences",
                [
                    "chicken options", "risotto", "vegetarian", "vegan", "seafood",
                    "Indian", "Chinese", "Thai", "Mexican",
                ],
                default=["chicken options"],
                key="manual_food",
            )
            must_include = st.multiselect(
                "Include", ["activity", "dinner", "dessert"], default=["activity", "dinner"]
            )
            max_leg = st.slider("Maximum travel per leg", min_value=5, max_value=60, value=30)
        submitted = st.form_submit_button("Build manual plan", use_container_width=True)

    if submitted:
        if not city.strip():
            st.warning("Enter a city.")
        elif not start_area.strip():
            st.warning("Enter a starting area.")
        elif not must_include:
            st.warning("Select at least one stop category.")
        else:
            payload = {
                "city": city.strip(),
                "start_area": start_area.strip(),
                "date": date.strip(),
                "start_time": start_time.strftime("%H:%M"),
                "budget_total": budget,
                "party_size": party_size,
                "transport": transport,
                "vibe": vibe,
                "must_include": must_include,
                "food_preferences": food,
                "max_leg_minutes": max_leg,
            }
            try:
                with st.spinner("Building manual plan..."):
                    result = request_json("/plans", payload)
            except requests.Timeout:
                st.error("The request took too long.")
            except requests.ConnectionError:
                st.error(f"PlanPilot could not connect to {BACKEND_URL}.")
            except requests.HTTPError as exc:
                st.error("The backend rejected the manual request.")
                if exc.response is not None and exc.response.text:
                    st.code(exc.response.text)
            except (requests.RequestException, ValueError) as exc:
                st.error(f"Could not build plans: {exc}")
            else:
                save_result(result)
                st.rerun()
