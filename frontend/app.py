import os
from datetime import time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000",
)

st.set_page_config(
    page_title="PlanPilot",
    page_icon="🧭",
    layout="wide",
)

st.title("🧭 PlanPilot")
st.caption(
    "Constraint-aware AI date and outing planner — V1"
)


def render_plans(result: dict) -> None:
    st.info(result["data_notice"])

    parsed = result.get("parsed_request")
    if parsed:
        with st.expander("What PlanPilot understood"):
            st.json(parsed)

    plans = result.get("plans", [])

    if not plans:
        st.warning("No matching plans were found.")
        return

    for index, plan in enumerate(plans, start=1):
        with st.container(border=True):
            st.subheader(
                f"Option {index}: {plan['title']}"
            )

            metric1, metric2, metric3 = st.columns(3)

            metric1.metric(
                "Estimated total",
                f"${plan['total_cost']:.0f}",
            )

            metric2.metric(
                "Estimated travel",
                f"{plan['estimated_travel_minutes']} min",
            )

            hours = plan["total_duration_minutes"] // 60
            minutes = plan["total_duration_minutes"] % 60

            metric3.metric(
                "Total outing",
                f"{hours}h {minutes}m",
            )

            st.markdown("#### Itinerary")

            for stop in plan["stops"]:
                st.write(
                    f"**{stop['category'].title()}:** "
                    f"{stop['name']} — {stop['area']} "
                    f"(${stop['estimated_cost']:.0f})"
                )

            st.markdown("#### Why this plan works")

            for reason in plan["reasons"]:
                st.write(f"• {reason}")

            for warning in plan.get("warnings", []):
                st.warning(warning)

    if result.get("llm_explanation"):
        st.subheader("PlanPilot explanation")
        st.write(result["llm_explanation"])


st.header("Plan with one message")

natural_language_request = st.text_area(
    "Describe the outing you want",
    placeholder=(
        "Plan a romantic date in Boston this Friday "
        "after 6 PM for two people under $180. "
        "Include dinner and dessert. We have no car."
    ),
    height=140,
)

natural_col1, natural_col2 = st.columns(2)

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
        ],
        default=[],
        key="natural_food_preferences",
    )

if st.button(
    "Generate plans from my request",
    type="primary",
):
    if not natural_language_request.strip():
        st.warning("Describe the outing first.")
    else:
        payload = {
            "text": natural_language_request,
            "start_area": natural_start_area,
            "food_preferences": natural_food_preferences,
        }

        try:
            with st.spinner(
                "Understanding your request and building plans..."
            ):
                response = requests.post(
                    f"{BACKEND_URL}/plan-from-text",
                    json=payload,
                    timeout=60,
                )

                response.raise_for_status()
                result = response.json()

        except requests.RequestException as exc:
            st.error(
                f"Could not generate plans: {exc}"
            )
        else:
            st.success("Your plans are ready.")
            render_plans(result)


st.divider()

with st.expander("Use the manual planner"):
    with st.form("plan_form"):
        col1, col2 = st.columns(2)

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
                "Date",
                "Friday",
            )

            start_time = st.time_input(
                "Start time",
                value=time(17, 0),
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
                    "scenic",
                    "cozy",
                    "stylish",
                    "active",
                    "indoor",
                ],
                default=["romantic", "fun"],
            )

            food = st.multiselect(
                "Food preferences",
                [
                    "chicken options",
                    "risotto",
                ],
                default=["chicken options"],
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
            "Build manual plans"
        )

    if submitted:
        payload = {
            "city": city,
            "start_area": start_area,
            "date": date,
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
            with st.spinner("Building plans..."):
                response = requests.post(
                    f"{BACKEND_URL}/plans",
                    json=payload,
                    timeout=60,
                )

                response.raise_for_status()
                result = response.json()

        except requests.RequestException as exc:
            st.error(
                f"Could not reach the backend: {exc}"
            )
        else:
            render_plans(result)
