from __future__ import annotations

import os
import re
from datetime import time
from typing import Any

import pydeck as pdk
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


def get_backend_url() -> str:
    """
    Resolve the PlanPilot backend URL.

    Streamlit Community Cloud stores deployment values in st.secrets.
    Local development continues to use the .env environment variable.
    """

    try:
        secret_backend_url = st.secrets.get(
            "BACKEND_URL"
        )

        if secret_backend_url:
            return (
                str(
                    secret_backend_url
                )
                .strip()
                .rstrip("/")
            )

    except Exception:
        pass

    return (
        os.getenv(
            "BACKEND_URL",
            "http://localhost:8000",
        )
        .strip()
        .rstrip("/")
    )


BACKEND_URL = get_backend_url()


st.set_page_config(
    page_title="PlanPilot",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .hero {
            padding: 1.5rem 1.6rem;
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 18px;
            margin-bottom: 1.3rem;
            background:
                linear-gradient(
                    135deg,
                    rgba(79, 70, 229, 0.12),
                    rgba(14, 165, 233, 0.08)
                );
        }

        .hero h1 {
            margin: 0;
            font-size: 2.6rem;
        }

        .hero p {
            margin-top: 0.5rem;
            margin-bottom: 0;
            opacity: 0.8;
            font-size: 1.05rem;
        }

        .plan-label {
            display: inline-block;
            padding: 0.28rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            background: rgba(79, 70, 229, 0.14);
            border: 1px solid rgba(79, 70, 229, 0.25);
            margin-bottom: 0.55rem;
        }

        .source-badge {
            display: inline-block;
            padding: 0.18rem 0.5rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 650;
            background: rgba(14, 165, 233, 0.12);
            border: 1px solid rgba(14, 165, 233, 0.24);
        }

        .category-badge {
            display: inline-block;
            padding: 0.18rem 0.48rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 650;
            background: rgba(128, 128, 128, 0.12);
            border: 1px solid rgba(128, 128, 128, 0.22);
            margin-right: 0.35rem;
        }

        .routing-live-badge {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 700;
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.25);
            margin-right: 0.35rem;
        }

        .routing-fallback-badge {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            font-size: 0.74rem;
            font-weight: 700;
            background: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.25);
            margin-right: 0.35rem;
        }

        .stop-card {
            padding: 1rem 1.1rem;
            margin: 0.55rem 0;
            border-radius: 14px;
            border: 1px solid rgba(128, 128, 128, 0.20);
            background: rgba(128, 128, 128, 0.035);
        }

        .stop-title {
            font-size: 1.08rem;
            font-weight: 750;
            margin-top: 0.4rem;
            margin-bottom: 0.25rem;
        }

        .stop-details {
            opacity: 0.80;
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .timeline-arrow {
            text-align: center;
            font-size: 1.25rem;
            opacity: 0.5;
            margin: 0.1rem 0;
        }

        .notice-box {
            padding: 0.85rem 1rem;
            border-radius: 12px;
            border: 1px solid rgba(14, 165, 233, 0.20);
            background: rgba(14, 165, 233, 0.07);
            margin-bottom: 1rem;
        }

        .route-leg {
            padding: 0.7rem 0.85rem;
            border-radius: 10px;
            border: 1px solid rgba(128, 128, 128, 0.14);
            margin-bottom: 0.45rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.16);
            padding: 0.8rem;
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="hero">
        <h1>🧭 PlanPilot</h1>
        <p>
            Agentic AI planning for dates, group outings and local
            experiences — built around your budget, timing, travel
            limits and preferences.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def category_icon(category: str) -> str:
    icons = {
        "activity": "🎟️",
        "restaurant": "🍽️",
        "dessert": "🍨",
    }

    return icons.get(
        category.lower(),
        "📍",
    )


def transport_icon(mode: str) -> str:
    icons = {
        "walking": "🚶",
        "driving": "🚗",
        "public_transit": "🚇",
    }

    return icons.get(
        mode,
        "🧭",
    )


def format_duration(minutes: int | float) -> str:
    total_minutes = int(minutes)

    hours, remaining_minutes = divmod(
        total_minutes,
        60,
    )

    if hours and remaining_minutes:
        return f"{hours}h {remaining_minutes}m"

    if hours:
        return f"{hours}h"

    return f"{remaining_minutes}m"


def format_distance(
    distance_meters: int | float,
) -> str:
    meters = float(distance_meters)

    if meters >= 1000:
        return f"{meters / 1000:.1f} km"

    return f"{int(meters)} m"


def extract_schedule(
    reasons: list[str],
) -> dict[str, str]:
    schedule_reason = next(
        (
            reason
            for reason in reasons
            if reason.startswith(
                "Estimated schedule:"
            )
        ),
        None,
    )

    if not schedule_reason:
        return {}

    schedule_text = (
        schedule_reason
        .removeprefix(
            "Estimated schedule:"
        )
        .strip()
        .rstrip(".")
    )

    schedule: dict[str, str] = {}

    for segment in schedule_text.split("→"):
        cleaned_segment = segment.strip()

        match = re.match(
            r"(.+?)\s+at\s+"
            r"(\d{1,2}:\d{2}\s+[AP]M)$",
            cleaned_segment,
        )

        if not match:
            continue

        venue_name = (
            match.group(1).strip()
        )

        arrival_time = (
            match.group(2).strip()
        )

        schedule[venue_name] = (
            arrival_time
        )

    return schedule


def request_json(
    endpoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = requests.post(
        f"{BACKEND_URL}{endpoint}",
        json=payload,
        timeout=180,
    )

    response.raise_for_status()

    result = response.json()

    if not isinstance(
        result,
        dict,
    ):
        raise ValueError(
            "The backend returned an unexpected response."
        )

    return result


def route_geometry_to_path(
    route_leg: dict[str, Any],
) -> list[list[float]]:
    geometry = route_leg.get(
        "geometry",
        [],
    )

    path: list[list[float]] = []

    if not isinstance(
        geometry,
        list,
    ):
        return path

    for point in geometry:
        if not isinstance(
            point,
            dict,
        ):
            continue

        latitude = point.get(
            "latitude"
        )

        longitude = point.get(
            "longitude"
        )

        if (
            latitude is None
            or longitude is None
        ):
            continue

        path.append(
            [
                float(longitude),
                float(latitude),
            ]
        )

    return path


def calculate_map_zoom(
    coordinates: list[
        tuple[float, float]
    ],
) -> float:
    if len(coordinates) <= 1:
        return 14.0

    latitudes = [
        latitude
        for latitude, _
        in coordinates
    ]

    longitudes = [
        longitude
        for _, longitude
        in coordinates
    ]

    latitude_span = (
        max(latitudes)
        - min(latitudes)
    )

    longitude_span = (
        max(longitudes)
        - min(longitudes)
    )

    span = max(
        latitude_span,
        longitude_span,
    )

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


def build_map_data(
    plan: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[tuple[float, float]],
]:
    route_legs = list(
        plan.get(
            "route_legs",
            [],
        )
    )

    stops = list(
        plan.get(
            "stops",
            [],
        )
    )

    route_paths: list[
        dict[str, Any]
    ] = []

    stop_markers: list[
        dict[str, Any]
    ] = []

    start_markers: list[
        dict[str, Any]
    ] = []

    all_coordinates: list[
        tuple[float, float]
    ] = []

    for leg_index, leg in enumerate(
        route_legs,
        start=1,
    ):
        path = (
            route_geometry_to_path(
                leg
            )
        )

        if len(path) >= 2:
            provider = str(
                leg.get(
                    "provider",
                    "unknown",
                )
            )

            fallback_used = bool(
                leg.get(
                    "fallback_used",
                    False,
                )
            )

            route_paths.append(
                {
                    "path": path,
                    "name": (
                        f"{leg.get('from_name', 'Start')} "
                        f"→ "
                        f"{leg.get('to_name', 'Destination')}"
                    ),
                    "from_name": leg.get(
                        "from_name",
                        "Start",
                    ),
                    "to_name": leg.get(
                        "to_name",
                        "Destination",
                    ),
                    "duration": format_duration(
                        leg.get(
                            "duration_minutes",
                            0,
                        )
                    ),
                    "distance": format_distance(
                        leg.get(
                            "distance_meters",
                            0,
                        )
                    ),
                    "provider": provider,
                    "route_type": (
                        "Estimated"
                        if fallback_used
                        else "Live"
                    ),
                }
            )

            for (
                longitude,
                latitude,
            ) in path:
                all_coordinates.append(
                    (
                        latitude,
                        longitude,
                    )
                )

            if (
                leg_index == 1
                and path
            ):
                start_longitude = (
                    path[0][0]
                )

                start_latitude = (
                    path[0][1]
                )

                start_markers.append(
                    {
                        "longitude": (
                            start_longitude
                        ),
                        "latitude": (
                            start_latitude
                        ),
                        "label": "S",
                        "name": leg.get(
                            "from_name",
                            "Starting point",
                        ),
                        "category": (
                            "Starting point"
                        ),
                    }
                )

    for stop_index, stop in enumerate(
        stops,
        start=1,
    ):
        latitude = stop.get(
            "latitude"
        )

        longitude = stop.get(
            "longitude"
        )

        if (
            latitude is None
            or longitude is None
        ):
            continue

        latitude_value = float(
            latitude
        )

        longitude_value = float(
            longitude
        )

        stop_markers.append(
            {
                "longitude": (
                    longitude_value
                ),
                "latitude": (
                    latitude_value
                ),
                "label": str(
                    stop_index
                ),
                "name": stop.get(
                    "name",
                    f"Stop {stop_index}",
                ),
                "category": str(
                    stop.get(
                        "category",
                        "stop",
                    )
                ).title(),
                "area": stop.get(
                    "area",
                    "",
                ),
            }
        )

        all_coordinates.append(
            (
                latitude_value,
                longitude_value,
            )
        )

    return (
        route_paths,
        stop_markers,
        start_markers,
        all_coordinates,
    )


def render_plan_map(
    plan: dict[str, Any],
    plan_number: int,
) -> None:
    (
        route_paths,
        stop_markers,
        start_markers,
        all_coordinates,
    ) = build_map_data(
        plan
    )

    if not all_coordinates:
        st.info(
            "Map data is not available for this plan."
        )
        return

    center_latitude = (
        sum(
            coordinate[0]
            for coordinate
            in all_coordinates
        )
        / len(all_coordinates)
    )

    center_longitude = (
        sum(
            coordinate[1]
            for coordinate
            in all_coordinates
        )
        / len(all_coordinates)
    )

    zoom = calculate_map_zoom(
        all_coordinates
    )

    layers: list[
        pdk.Layer
    ] = []

    if route_paths:
        route_layer = pdk.Layer(
            "PathLayer",
            data=route_paths,
            get_path="path",
            get_width=6,
            get_color=[59, 130, 246],
            width_min_pixels=5,
            pickable=True,
            auto_highlight=True,
        )

        layers.append(
            route_layer
        )

    if start_markers:
        start_marker_layer = pdk.Layer(
            "ScatterplotLayer",
            data=start_markers,
            get_position=(
                "[longitude, latitude]"
            ),
            get_radius=70,
            get_fill_color=[
                16,
                185,
                129,
            ],
            get_line_color=[
                255,
                255,
                255,
            ],
            radius_min_pixels=11,
            radius_max_pixels=18,
            pickable=True,
            stroked=True,
            filled=True,
            line_width_min_pixels=2,
        )

        start_text_layer = pdk.Layer(
            "TextLayer",
            data=start_markers,
            get_position=(
                "[longitude, latitude]"
            ),
            get_text="label",
            get_color=[
                255,
                255,
                255,
            ],
            get_size=14,
            size_min_pixels=12,
            size_max_pixels=18,
            get_alignment_baseline=(
                "'center'"
            ),
            get_text_anchor=(
                "'middle'"
            ),
            pickable=False,
        )

        layers.extend(
            [
                start_marker_layer,
                start_text_layer,
            ]
        )

    if stop_markers:
        stop_layer = pdk.Layer(
            "ScatterplotLayer",
            data=stop_markers,
            get_position=(
                "[longitude, latitude]"
            ),
            get_radius=75,
            get_fill_color=[
                239,
                68,
                68,
            ],
            get_line_color=[
                255,
                255,
                255,
            ],
            radius_min_pixels=11,
            radius_max_pixels=18,
            pickable=True,
            stroked=True,
            filled=True,
            line_width_min_pixels=2,
        )

        number_layer = pdk.Layer(
            "TextLayer",
            data=stop_markers,
            get_position=(
                "[longitude, latitude]"
            ),
            get_text="label",
            get_color=[
                255,
                255,
                255,
            ],
            get_size=15,
            size_min_pixels=12,
            size_max_pixels=19,
            get_alignment_baseline=(
                "'center'"
            ),
            get_text_anchor=(
                "'middle'"
            ),
            pickable=False,
        )

        layers.extend(
            [
                stop_layer,
                number_layer,
            ]
        )

    deck = pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=(
                center_latitude
            ),
            longitude=(
                center_longitude
            ),
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),
        layers=layers,
        tooltip={
            "html": (
                "<b>{name}</b><br/>"
                "{category}<br/>"
                "{area}"
                "{duration}"
                "{distance}"
                "{provider}"
            ),
            "style": {
                "backgroundColor": (
                    "#111827"
                ),
                "color": "white",
            },
        },
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
        key=(
            f"plan_map_{plan_number}"
        ),
    )


def render_route_summary(
    route_legs: list[
        dict[str, Any]
    ],
) -> None:
    if not route_legs:
        return

    total_distance = sum(
        int(
            leg.get(
                "distance_meters",
                0,
            )
        )
        for leg in route_legs
    )

    live_count = sum(
        1
        for leg in route_legs
        if not bool(
            leg.get(
                "fallback_used",
                False,
            )
        )
    )

    fallback_count = (
        len(route_legs)
        - live_count
    )

    (
        route_col1,
        route_col2,
        route_col3,
    ) = st.columns(
        3
    )

    route_col1.metric(
        "Route distance",
        format_distance(
            total_distance
        ),
    )

    route_col2.metric(
        "Live route legs",
        live_count,
    )

    route_col3.metric(
        "Fallback legs",
        fallback_count,
    )

    badges = ""

    if live_count:
        badges += (
            '<span class="routing-live-badge">'
            f"✓ {live_count} live route"
            f"{'s' if live_count != 1 else ''}"
            "</span>"
        )

    if fallback_count:
        badges += (
            '<span class="routing-fallback-badge">'
            f"~ {fallback_count} estimated route"
            f"{'s' if fallback_count != 1 else ''}"
            "</span>"
        )

    if badges:
        st.markdown(
            badges,
            unsafe_allow_html=True,
        )

    with st.expander(
        "Route breakdown"
    ):
        for index, leg in enumerate(
            route_legs,
            start=1,
        ):
            from_name = str(
                leg.get(
                    "from_name",
                    "Start",
                )
            )

            to_name = str(
                leg.get(
                    "to_name",
                    "Destination",
                )
            )

            minutes = int(
                leg.get(
                    "duration_minutes",
                    0,
                )
            )

            distance = int(
                leg.get(
                    "distance_meters",
                    0,
                )
            )

            mode = str(
                leg.get(
                    "mode",
                    "unknown",
                )
            )

            provider = str(
                leg.get(
                    "provider",
                    "unknown",
                )
            )

            fallback_used = bool(
                leg.get(
                    "fallback_used",
                    False,
                )
            )

            route_source = (
                "Estimated fallback"
                if fallback_used
                else "Live routing"
            )

            st.markdown(
                f"""
                <div class="route-leg">
                    <strong>
                        Leg {index}: {from_name} → {to_name}
                    </strong>
                    <br>
                    {transport_icon(mode)}
                    {format_duration(minutes)}
                    &nbsp;&nbsp;•&nbsp;&nbsp;
                    📏 {format_distance(distance)}
                    &nbsp;&nbsp;•&nbsp;&nbsp;
                    {route_source}
                    &nbsp;&nbsp;•&nbsp;&nbsp;
                    Provider: {provider}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_stop(
    stop: dict[str, Any],
    arrival_time: str | None,
) -> None:
    category = str(
        stop.get(
            "category",
            "stop",
        )
    )

    name = str(
        stop.get(
            "name",
            "Unknown venue",
        )
    )

    area = str(
        stop.get(
            "area",
            "Area unavailable",
        )
    )

    cost = float(
        stop.get(
            "estimated_cost",
            0,
        )
    )

    duration = int(
        stop.get(
            "duration_minutes",
            0,
        )
    )

    source = str(
        stop.get(
            "source",
            "estimated",
        )
    )

    formatted_address = stop.get(
        "formatted_address"
    )

    opening_hours = stop.get(
        "opening_hours"
    )

    website = stop.get(
        "website"
    )

    top_badges = (
        f'<span class="category-badge">'
        f"{category_icon(category)} "
        f"{category.title()}"
        f"</span>"
    )

    if source == "geoapify":
        top_badges += (
            '<span class="source-badge">'
            "Live place data"
            "</span>"
        )

    timing_text = (
        f"Arrival: {arrival_time}"
        if arrival_time
        else "Arrival time unavailable"
    )

    st.markdown(
        f"""
        <div class="stop-card">
            <div>{top_badges}</div>
            <div class="stop-title">{name}</div>
            <div class="stop-details">
                📍 {area}<br>
                🕒 {timing_text}
                &nbsp;&nbsp;•&nbsp;&nbsp;
                Stay: {format_duration(duration)}<br>
                💳 Estimated cost for group: ${cost:.0f}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    detail_columns = st.columns(
        [
            1.2,
            1.2,
            0.8,
        ],
    )

    with detail_columns[0]:
        if formatted_address:
            st.caption(
                f"Address: {formatted_address}"
            )
        else:
            st.caption(
                "Address unavailable"
            )

    with detail_columns[1]:
        if opening_hours:
            st.caption(
                f"Hours data: {opening_hours}"
            )
        else:
            st.caption(
                "Hours not provided by the live source"
            )

    with detail_columns[2]:
        if website:
            st.link_button(
                "Open venue website ↗",
                website,
                use_container_width=True,
            )


def render_plan(
    plan: dict[str, Any],
    plan_number: int,
) -> None:
    label = str(
        plan.get(
            "label",
            f"Option {plan_number}",
        )
    )

    title = str(
        plan.get(
            "title",
            "Plan option",
        )
    )

    total_cost = float(
        plan.get(
            "total_cost",
            0,
        )
    )

    travel_minutes = int(
        plan.get(
            "estimated_travel_minutes",
            0,
        )
    )

    total_duration = int(
        plan.get(
            "total_duration_minutes",
            0,
        )
    )

    reasons = list(
        plan.get(
            "reasons",
            [],
        )
    )

    warnings = list(
        plan.get(
            "warnings",
            [],
        )
    )

    stops = list(
        plan.get(
            "stops",
            [],
        )
    )

    route_legs = list(
        plan.get(
            "route_legs",
            [],
        )
    )

    schedule = extract_schedule(
        reasons
    )

    with st.container(
        border=True
    ):
        st.markdown(
            (
                f'<span class="plan-label">'
                f"{label}"
                "</span>"
            ),
            unsafe_allow_html=True,
        )

        st.subheader(
            title
        )

        (
            metric1,
            metric2,
            metric3,
            metric4,
        ) = st.columns(
            4
        )

        metric1.metric(
            "Estimated total",
            f"${total_cost:.0f}",
        )

        metric2.metric(
            "Travel time",
            format_duration(
                travel_minutes
            ),
        )

        metric3.metric(
            "Full outing",
            format_duration(
                total_duration
            ),
        )

        metric4.metric(
            "Stops",
            len(stops),
        )

        if warnings:
            for warning in warnings:
                st.warning(
                    warning,
                    icon="⚠️",
                )
        else:
            st.success(
                "No availability, budget or travel warnings.",
                icon="✅",
            )

        st.markdown(
            "#### 🗺️ Itinerary map"
        )

        if route_legs:
            render_plan_map(
                plan=plan,
                plan_number=(
                    plan_number
                ),
            )

            render_route_summary(
                route_legs
            )

        else:
            st.info(
                "Route information is not available for this plan."
            )

        st.markdown(
            "#### Your itinerary"
        )

        for stop_index, stop in enumerate(
            stops
        ):
            render_stop(
                stop=stop,
                arrival_time=(
                    schedule.get(
                        str(
                            stop.get(
                                "name",
                                "",
                            )
                        )
                    )
                ),
            )

            if (
                stop_index
                < len(stops) - 1
            ):
                st.markdown(
                    (
                        '<div class="timeline-arrow">'
                        "↓"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

        with st.expander(
            "Why PlanPilot selected this option"
        ):
            displayed_reasons = [
                reason
                for reason in reasons
                if not reason.startswith(
                    "Estimated schedule:"
                )
            ]

            for reason in displayed_reasons:
                st.write(
                    f"• {reason}"
                )


def render_plans(
    result: dict[str, Any],
) -> None:
    data_notice = result.get(
        "data_notice"
    )

    if data_notice:
        st.markdown(
            f"""
            <div class="notice-box">
                <strong>Data notice</strong><br>
                {data_notice}
            </div>
            """,
            unsafe_allow_html=True,
        )

    summary_columns = st.columns(
        3
    )

    used_live_data = bool(
        result.get(
            "used_live_data",
            False,
        )
    )

    candidate_count = result.get(
        "venue_candidate_count"
    )

    start_coordinates = result.get(
        "start_coordinates"
    )

    summary_columns[0].metric(
        "Place data",
        (
            "Live"
            if used_live_data
            else "Sample"
        ),
    )

    summary_columns[1].metric(
        "Candidates checked",
        (
            candidate_count
            if candidate_count
            is not None
            else "—"
        ),
    )

    summary_columns[2].metric(
        "Starting point located",
        (
            "Yes"
            if start_coordinates
            else "No"
        ),
    )

    parsed = result.get(
        "parsed_request"
    )

    planning_request = result.get(
        "planning_request"
    )

    with st.expander(
        "What PlanPilot understood"
    ):
        if parsed:
            st.markdown(
                "**Natural-language interpretation**"
            )

            st.json(
                parsed
            )

        if planning_request:
            st.markdown(
                "**Final planning constraints**"
            )

            st.json(
                planning_request
            )

    plans = result.get(
        "plans",
        [],
    )

    if not plans:
        st.warning(
            "No viable plans matched all of the current "
            "constraints. Try increasing the budget, travel "
            "limit or start time."
        )
        return

    st.markdown(
        "## Recommended plans"
    )

    tabs = st.tabs(
        [
            str(
                plan.get(
                    "label",
                    f"Option {index}",
                )
            )
            for index, plan in enumerate(
                plans,
                start=1,
            )
        ]
    )

    for index, (
        tab,
        plan,
    ) in enumerate(
        zip(
            tabs,
            plans,
            strict=True,
        ),
        start=1,
    ):
        with tab:
            render_plan(
                plan=plan,
                plan_number=index,
            )

    llm_explanation = result.get(
        "llm_explanation"
    )

    if llm_explanation:
        st.markdown(
            "## PlanPilot explanation"
        )

        st.write(
            llm_explanation
        )


def save_result(
    result: dict[str, Any],
) -> None:
    st.session_state[
        "planpilot_result"
    ] = result


def display_saved_result() -> None:
    result = st.session_state.get(
        "planpilot_result"
    )

    if result:
        st.divider()

        render_plans(
            result
        )


st.markdown(
    "## Plan with one message"
)

st.caption(
    "Describe the experience naturally. PlanPilot will extract "
    "the city, budget, group size, vibe, transport and required stops."
)

natural_language_request = st.text_area(
    "Describe the outing you want",
    placeholder=(
        "Plan a chill rainy-day outing in Boston for two people "
        "under $150 with an activity, dinner and dessert."
    ),
    height=150,
)

natural_col1, natural_col2 = st.columns(
    2
)

with natural_col1:
    natural_start_area = st.text_input(
        "Starting area",
        value="Davis Square",
        key="natural_start_area",
    )

with natural_col2:
    natural_food_preferences = st.multiselect(
        "Food preferences",
        [
            "chicken options",
            "risotto",
            "vegetarian",
            "vegan",
            "seafood",
            "Indian",
            "Chinese",
            "Thai",
            "Mexican",
        ],
        default=[],
        key="natural_food_preferences",
    )


generate_live_plans = st.button(
    "Generate live plans",
    type="primary",
    use_container_width=True,
)


if generate_live_plans:
    if not natural_language_request.strip():
        st.warning(
            "Describe the outing first."
        )

    elif not natural_start_area.strip():
        st.warning(
            "Enter a starting area."
        )

    else:
        payload = {
            "text": (
                natural_language_request.strip()
            ),
            "start_area": (
                natural_start_area.strip()
            ),
            "food_preferences": (
                natural_food_preferences
            ),
        }

        try:
            with st.spinner(
                "Searching live places, checking hours, "
                "routing between stops and ranking plans..."
            ):
                result = request_json(
                    endpoint=(
                        "/plan-from-text/live/"
                    ),
                    payload=payload,
                )

        except requests.Timeout:
            st.error(
                "The request took too long. Confirm that the "
                "backend is running and try again."
            )

        except requests.ConnectionError:
            st.error(
                "PlanPilot could not connect to the backend at "
                f"{BACKEND_URL}."
            )

        except requests.HTTPError as exc:
            response_text = ""

            if (
                exc.response
                is not None
            ):
                response_text = (
                    exc.response.text
                )

            st.error(
                "The backend rejected the request."
            )

            if response_text:
                st.code(
                    response_text
                )

        except (
            requests.RequestException,
            ValueError,
        ) as exc:
            st.error(
                f"Could not generate plans: {exc}"
            )

        else:
            save_result(
                result
            )

            st.success(
                "Your live plans are ready."
            )


st.divider()


with st.expander(
    "Use the manual planner"
):
    with st.form(
        "plan_form"
    ):
        col1, col2 = st.columns(
            2
        )

        with col1:
            city = st.text_input(
                "City",
                "Boston",
            )

            start_area = st.text_input(
                "Starting area",
                "Davis Square",
                key="manual_start_area",
            )

            date = st.text_input(
                "Date or weekday",
                "Friday",
            )

            start_time = st.time_input(
                "Start time",
                value=time(
                    17,
                    0,
                ),
            )

            budget = st.number_input(
                "Total budget ($)",
                min_value=20.0,
                value=200.0,
                step=10.0,
            )

        with col2:
            party_size = st.number_input(
                "People",
                min_value=1,
                max_value=12,
                value=2,
            )

            transport = st.selectbox(
                "Transport",
                [
                    "public_transit",
                    "walking",
                    "driving",
                ],
            )

            vibe = st.multiselect(
                "Vibe",
                [
                    "romantic",
                    "fun",
                    "chill",
                    "scenic",
                    "cozy",
                    "stylish",
                    "active",
                    "cultural",
                    "nightlife",
                    "family",
                    "foodie",
                    "budget",
                    "rainy-day",
                    "work-friendly",
                    "group",
                ],
                default=[
                    "romantic",
                    "fun",
                ],
            )

            food = st.multiselect(
                "Food preferences",
                [
                    "chicken options",
                    "risotto",
                    "vegetarian",
                    "vegan",
                    "seafood",
                    "Indian",
                    "Chinese",
                    "Thai",
                    "Mexican",
                ],
                default=[
                    "chicken options"
                ],
                key="manual_food",
            )

            must_include = st.multiselect(
                "Include",
                [
                    "activity",
                    "dinner",
                    "dessert",
                ],
                default=[
                    "activity",
                    "dinner",
                ],
            )

            max_leg = st.slider(
                "Maximum travel per leg",
                min_value=5,
                max_value=60,
                value=30,
            )

        submitted = st.form_submit_button(
            "Build manual plans",
            use_container_width=True,
        )


    if submitted:
        if not city.strip():
            st.warning(
                "Enter a city."
            )

        elif not start_area.strip():
            st.warning(
                "Enter a starting area."
            )

        elif not must_include:
            st.warning(
                "Select at least one stop category."
            )

        else:
            payload = {
                "city": city.strip(),
                "start_area": (
                    start_area.strip()
                ),
                "date": date.strip(),
                "start_time": (
                    start_time.strftime(
                        "%H:%M"
                    )
                ),
                "budget_total": budget,
                "party_size": party_size,
                "transport": transport,
                "vibe": vibe,
                "must_include": (
                    must_include
                ),
                "food_preferences": food,
                "max_leg_minutes": (
                    max_leg
                ),
            }

            try:
                with st.spinner(
                    "Building manual plans..."
                ):
                    result = request_json(
                        endpoint="/plans",
                        payload=payload,
                    )

            except requests.Timeout:
                st.error(
                    "The request took too long."
                )

            except requests.ConnectionError:
                st.error(
                    "PlanPilot could not connect to "
                    f"{BACKEND_URL}."
                )

            except requests.HTTPError as exc:
                response_text = ""

                if (
                    exc.response
                    is not None
                ):
                    response_text = (
                        exc.response.text
                    )

                st.error(
                    "The backend rejected the manual request."
                )

                if response_text:
                    st.code(
                        response_text
                    )

            except (
                requests.RequestException,
                ValueError,
            ) as exc:
                st.error(
                    f"Could not build plans: {exc}"
                )

            else:
                save_result(
                    result
                )

                st.success(
                    "Your manual plans are ready."
                )


display_saved_result()
