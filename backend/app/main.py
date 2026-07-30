from fastapi import FastAPI

from .llm import explain_plan_with_llm, llm_is_configured
from .models import PlanRequest
from .planner import build_plans

app = FastAPI(title="PlanPilot API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_configured": llm_is_configured()}


@app.post("/plans")
def create_plans(request: PlanRequest) -> dict:
    plans = build_plans(request)
    serialized = [plan.model_dump() for plan in plans]
    explanation = explain_plan_with_llm(request.model_dump(), serialized)
    return {
        "request": request,
        "plans": serialized,
        "llm_explanation": explanation,
        "data_notice": "V1 uses sample venue and route data. Live APIs arrive in Phase 2.",
    }
