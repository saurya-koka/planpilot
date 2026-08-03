# PlanPilot

PlanPilot is a constraint-aware, agentic AI planner for dates, local outings, and city experiences.

It converts a natural-language request into multiple ranked itineraries while checking budget, travel limits, venue categories, opening hours, visit duration, transportation preferences, and user constraints.

## Why PlanPilot

Most itinerary tools return generic lists of places. PlanPilot instead builds complete, ranked outing plans that are:

- budget-aware;
- time-aware;
- travel-aware;
- availability-aware;
- tailored to the requested vibe and required stops;
- explainable through deterministic scoring and validation.

## Key Features

- Natural-language outing requests
- Structured constraint extraction
- Live Geoapify place search
- Starting-location geocoding
- Coordinate-based travel estimates
- Budget-aware itinerary generation
- Activity, dinner, and dessert planning
- Intent-aware venue search
- Multiple ranked itinerary options
- Opening-hours validation
- Full-visit availability checking
- Complex weekday schedule parsing
- Multiple daily opening intervals
- Near-duplicate venue cleanup
- Optional OpenAI language layer
- FastAPI backend
- Streamlit frontend
- Automated pytest coverage

## Example Request

```text
Plan a chill rainy-day outing in Boston for two people under $150
with an activity, dinner, and dessert.
```

## What PlanPilot Returns

PlanPilot generates three ranked itinerary options:

- Best overall
- Lowest cost
- Best vibe match

Each plan includes:

- estimated group cost;
- estimated travel time;
- total outing duration;
- arrival times for each stop;
- venue addresses;
- opening-hours information;
- venue website links;
- availability warnings;
- reasons the plan was selected.

## Architecture

```text
Natural-language request
        |
        v
Streamlit frontend
        |
        v
FastAPI backend
        |
        v
Request parser
        |
        v
Live Geoapify place search
        |
        v
Candidate validation and duplicate cleanup
        |
        v
Routing and schedule generation
        |
        v
Opening-hours and full-visit validation
        |
        v
Constraint scoring and plan ranking
        |
        v
Three recommended itineraries
```

The optional language model is used for interpreting ambiguous requests and generating explanations.

Deterministic Python logic handles:

- costs;
- scheduling;
- travel limits;
- venue validation;
- opening hours;
- full-visit checks;
- constraint enforcement;
- plan scoring and ranking.

## Technology Stack

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### Frontend

- Streamlit
- Requests

### APIs and Services

- Geoapify Places API
- OpenAI API, optional

### Testing

- pytest
- FastAPI TestClient
- httpx

## Project Structure

```text
planpilot/
├── backend/
│   └── app/
│       ├── main.py
│       ├── models.py
│       ├── planner.py
│       ├── llm.py
│       ├── data.py
│       └── tools/
│           ├── places.py
│           ├── live_candidates.py
│           ├── routing.py
│           └── opening_hours.py
├── frontend/
│   └── app.py
├── tests/
│   ├── test_api.py
│   ├── test_parser.py
│   ├── test_places.py
│   ├── test_planner.py
│   └── test_opening_hours.py
├── .env.example
├── .gitignore
├── requirements.txt
├── pytest.ini
├── LICENSE
└── README.md
```

## Local Setup

This section is for developers who want to run PlanPilot on their own computer. You do not need to repeat these steps if the project is already working locally.

### 1. Clone the repository

```powershell
git clone https://github.com/saurya-koka/planpilot.git
cd planpilot
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the environment file

```powershell
Copy-Item .env.example .env
```

Add the required values to `.env`:

```env
GEOAPIFY_API_KEY=your_geoapify_key
PLACES_PROVIDER=geoapify

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5

BACKEND_URL=http://localhost:8000
```

Geoapify is required for live place search.

The OpenAI API key is optional.

Never commit the real `.env` file.

## Run PlanPilot

### Start the FastAPI backend

From the project root:

```powershell
uvicorn backend.app.main:app --reload
```

The backend runs at:

```text
http://localhost:8000
```

Interactive API documentation is available at:

```text
http://localhost:8000/docs
```

### Start the Streamlit frontend

Open a second PowerShell terminal:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run frontend/app.py
```

The interface normally opens at:

```text
http://localhost:8501
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check whether the backend is running |
| `POST` | `/plans` | Generate plans from structured constraints |
| `POST` | `/plan-from-text` | Parse and plan from natural language |
| `POST` | `/plan-from-text/live` | Generate plans using live place data |

The live endpoint performs:

- natural-language parsing;
- live place search;
- starting-area geocoding;
- candidate filtering;
- duplicate cleanup;
- travel estimation;
- schedule generation;
- opening-hours validation;
- full-visit validation;
- plan scoring and ranking.

## Tests

Run the complete test suite:

```powershell
pytest -q
```

Current result:

```text
50 passed
```

The remaining Starlette warning comes from the test-client dependency and does not indicate a failing PlanPilot test.

## Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `GEOAPIFY_API_KEY` | Live venue search and geocoding | Yes for live planning |
| `PLACES_PROVIDER` | Selects the place-data provider | Yes for live planning |
| `OPENAI_API_KEY` | Optional LLM parsing and explanation | No |
| `OPENAI_MODEL` | OpenAI model used by the optional language layer | Only with OpenAI |
| `BACKEND_URL` | FastAPI address used by Streamlit | Yes for the frontend |

## Current Status

- [x] Natural-language constraint extraction
- [x] Live place search
- [x] Starting-location geocoding
- [x] Coordinate-based travel estimates
- [x] Budget validation
- [x] Travel-limit validation
- [x] Opening-hours validation
- [x] Full-visit availability validation
- [x] Complex opening-hours parsing
- [x] Multiple daily opening intervals
- [x] Near-duplicate venue cleanup
- [x] Three ranked itinerary options
- [x] Streamlit frontend
- [x] Automated tests
- [ ] Production deployment

## Roadmap

- Weather-aware replanning
- Real transit-duration APIs
- Live movie and event discovery
- Saved and shareable itineraries
- User preference profiles
- Availability monitoring
- Evaluation dashboard
- Additional place providers

## Engineering Principle

Use language models for ambiguity and language.

Use deterministic software for facts, calculations, constraints, validation, permissions, and consequential decisions.

## Author

**Saurya Koka**

- GitHub: [saurya-koka](https://github.com/saurya-koka)
- Project repository: [PlanPilot](https://github.com/saurya-koka/planpilot)
