from __future__ import annotations

import os
import re
from datetime import time
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000",
).rstrip("/")


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


def extract_schedule(
    reasons: list[str],
) -> dict[str, str]:
    """
    Convert a reason such as:

    Estimated schedule: Museum at 5:20 PM → Dinner at 7:10 PM.

    into a venue-to-arrival-time mapping.
    """
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

    schedule_text = schedule_reason.removeprefix(
        "Estimated schedule:"
    ).strip()

    schedule_text = schedule_text.rstrip(
        "."
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

        venue_name = match.group(1).strip()
        arrival_time = match.group(2).strip()

        schedule[venue_name] = arrival_time

    return schedule


def request_json(
    endpoint: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    response = requests.post(
        f"{BACKEND_URL}{endpoint}",
        json=payload,
        timeout=90,
    )

    response.raise_for_status()

    result = response.json()

    if not isinstance(result, dict):
        raise ValueError(
            "The backend returned an unexpected response."
        )

    return result


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
        [1.2, 1.2, 0.8],
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

    schedule = extract_schedule(
        reasons
    )

    with st.container(border=True):
        st.markdown(
            f'<span class="plan-label">{label}</span>',
            unsafe_allow_html=True,
        )

        st.subheader(title)

        metric1, metric2, metric3, metric4 = st.columns(
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

        st.markdown("#### Your itinerary")

        for stop_index, stop in enumerate(
            stops
        ):
            render_stop(
                stop=stop,
                arrival_time=schedule.get(
                    str(
                        stop.get(
                            "name",
                            "",
                        )
                    )
                ),
            )

            if stop_index < len(stops) - 1:
                st.markdown(
                    '<div class="timeline-arrow">↓</div>',
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
            if candidate_count is not None
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
            st.json(parsed)

        if planning_request:
            st.markdown(
                "**Final planning constraints**"
            )
            st.json(planning_request)

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

    st.markdown("## Recommended plans")

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
        render_plans(result)


st.markdown("## Plan with one message")

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
            "text": natural_language_request.strip(),
            "start_area": natural_start_area.strip(),
            "food_preferences": (
                natural_food_preferences
            ),
        }

        try:
            with st.spinner(
                "Searching live places, checking hours, "
                "estimating travel and ranking plans..."
            ):
                result = request_json(
                    endpoint=(
                        "/plan-from-text/live"
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

            if exc.response is not None:
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
            save_result(result)

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

        submitted = (
            st.form_submit_button(
                "Build manual plans",
                use_container_width=True,
            )
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
                "max_leg_minutes": max_leg,
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

                if exc.response is not None:
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
                save_result(result)

                st.success(
                    "Your manual plans are ready."
                )


display_saved_result()
