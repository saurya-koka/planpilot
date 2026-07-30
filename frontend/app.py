import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="PlanPilot", page_icon="🧭", layout="wide")
st.title("🧭 PlanPilot")
st.caption("Constraint-aware date and outing planner — V1")

with st.form("plan_form"):
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City", "Boston")
        start_area = st.text_input("Starting area", "Davis Square")
        date = st.text_input("Date", "Friday")
        start_time = st.time_input("Start time")
        budget = st.number_input("Total budget ($)", min_value=20.0, value=200.0, step=10.0)
    with col2:
        party_size = st.number_input("People", min_value=1, max_value=12, value=2)
        transport = st.selectbox("Transport", ["public_transit", "walking", "driving"])
        vibe = st.multiselect("Vibe", ["romantic", "fun", "scenic", "cozy", "stylish", "active", "indoor"], default=["romantic", "fun"])
        food = st.multiselect("Food preferences", ["chicken options", "risotto"], default=["chicken options"])
        max_leg = st.slider("Maximum travel per leg (minutes)", 5, 60, 30)
    submitted = st.form_submit_button("Build my plans")

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
        "must_include": ["activity", "dinner"],
        "food_preferences": food,
        "max_leg_minutes": max_leg,
    }
    try:
        response = requests.post(f"{BACKEND_URL}/plans", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach the backend: {exc}")
    else:
        st.info(result["data_notice"])
        for index, plan in enumerate(result["plans"], start=1):
            with st.container(border=True):
                st.subheader(f"Option {index}: {plan['title']}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Estimated total", f"${plan['total_cost']:.0f}")
                m2.metric("Between-stop travel", f"{plan['estimated_travel_minutes']} min")
                m3.metric("Total outing", f"{plan['total_duration_minutes'] // 60}h {plan['total_duration_minutes'] % 60}m")
                for stop in plan["stops"]:
                    st.write(f"**{stop['category'].title()}:** {stop['name']} — {stop['area']} (${stop['estimated_cost']:.0f})")
                for reason in plan["reasons"]:
                    st.write(f"• {reason}")

        if result.get("llm_explanation"):
            st.subheader("PlanPilot explanation")
            st.write(result["llm_explanation"])
