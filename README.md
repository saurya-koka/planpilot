# PlanPilot 🧭

PlanPilot is a constraint-aware AI agent for planning realistic dates, local outings, and later full trips.

## What V1 demonstrates

- Structured user requirements
- Deterministic itinerary generation
- Budget and travel-leg validation
- Ranking multiple plans
- FastAPI backend
- Streamlit interface
- Optional OpenAI language layer
- Tests and Git-ready project structure

> V1 intentionally uses sample venue and route data. Live places, maps, weather, movies, and availability checks are Phase 2.

## Architecture

```text
Streamlit UI
    ↓
FastAPI /plans endpoint
    ↓
Candidate generator
    ↓
Constraint validator + scoring
    ↓
Optional LLM explanation
```

The LLM handles language and explanation. Python handles prices, constraints, scoring, and validation.

## Run locally on Windows

### 1. Open PowerShell in the project folder

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### 2. Start the backend

```powershell
uvicorn backend.app.main:app --reload
```

Backend docs: `http://localhost:8000/docs`

### 3. Start the UI in a second PowerShell window

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```

### 4. Run tests

```powershell
pytest
```

## Optional LLM setup

Add your API key to `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5
```

Never commit `.env`. It is excluded by `.gitignore`.

## Push to GitHub with GitHub CLI

After installing and signing into GitHub CLI:

```powershell
git init
git add .
git commit -m "Initial PlanPilot V1 scaffold"
git branch -M main
gh repo create planpilot --public --source=. --remote=origin --push
```

## Manual GitHub alternative

Create an empty repository named `planpilot` on GitHub, then run:

```powershell
git init
git add .
git commit -m "Initial PlanPilot V1 scaffold"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/planpilot.git
git push -u origin main
```

## Roadmap

- [x] V1 mock-data planner and validator
- [ ] Natural-language request extraction
- [ ] Live place search
- [ ] Transit route calculations
- [ ] Weather-aware replanning
- [ ] Movie/event discovery
- [ ] Availability monitoring
- [ ] User-approved preference memory
- [ ] Evaluation dashboard

## Important engineering principle

Use the LLM for ambiguity and language. Use deterministic software for facts, calculations, validation, permissions, and consequential actions.
