# 🧭 PlanPilot V2

**Agentic AI planning for dates, group outings, and local experiences.**

PlanPilot converts a natural-language request into constraint-aware, ranked itineraries using live place data, routing, weather signals, retrieval-augmented generation, deterministic validation, and optional LLM reasoning.

🌐 **Live App:** https://planpilot-ai.streamlit.app
⚙️ **Production API:** https://planpilot-api.onrender.com
💻 **Repository:** https://github.com/saurya-koka/planpilot

---

## What PlanPilot Does

A user can write:

```text
Plan a chill rainy-day outing in Boston for two people under $150
with an activity, dinner and dessert.
```

PlanPilot can extract constraints such as:

- city;
- starting area;
- total budget;
- group size;
- desired vibe;
- transportation mode;
- maximum travel time;
- food preferences;
- required stop categories;
- requested date and start time.

It then searches live places, evaluates candidate venues, builds complete itineraries, validates constraints, ranks alternatives, and explains why each option was selected.

Rather than returning a generic list of places, PlanPilot produces an executable outing plan.

---

# ✨ Key Capabilities

## Natural-Language Planning

PlanPilot accepts free-form trip and outing requests and converts them into structured planning constraints.

The parsing layer supports:

- city extraction;
- budgets;
- party size;
- start times;
- travel constraints;
- transportation preferences;
- food preferences;
- vibe preferences;
- required activities;
- dinner and dessert requirements.

An OpenAI-backed structured language layer can handle ambiguous natural-language requests.

---

## Live Place Discovery

PlanPilot integrates with **Geoapify** for live:

- venue search;
- geocoding;
- addresses;
- coordinates;
- place categories;
- opening-hours metadata;
- venue websites;
- route information when available.

Candidate generation also includes:

- intent-aware place queries;
- starting-location bias;
- category-aware retrieval;
- near-duplicate removal;
- fallback behavior when external providers cannot return complete data.

---

## Real Routing + Interactive Maps

PlanPilot calculates travel between itinerary stops and renders the resulting itinerary on an interactive map.

The interface can display:

- starting location;
- numbered itinerary stops;
- route geometry;
- total travel distance;
- travel time;
- routing provider;
- live-versus-fallback route status.

When a live route cannot be retrieved, PlanPilot explicitly labels the result as an estimated fallback instead of presenting it as verified live routing.

---

## Constraint-Aware Planning

The deterministic planning layer evaluates:

- budget limits;
- travel limits;
- required stops;
- total outing duration;
- visit duration;
- transportation mode;
- venue availability;
- opening hours;
- food preferences;
- starting location.

Plans that violate constraints can be rejected, repaired, or reranked.

---

## Structured Validation

Validation failures are represented as structured data instead of generic error strings.

The validation layer can detect issues such as:

- over-budget itineraries;
- missing required categories;
- excessive travel time;
- unavailable venues;
- incomplete plans;
- scheduling conflicts.

This makes validation usable by both the UI and the agentic repair workflow.

---

# 🤖 Agentic Planning

PlanPilot V2 includes an agentic planning pipeline built with **LangGraph**.

The graph can coordinate:

```text
Initialize request
       ↓
Check weather
       ↓
Apply weather constraints
       ↓
Retrieve relevant venues
       ↓
Build candidate plans
       ↓
Validate constraints
       ↓
        ├── Valid → Finish
        │
        └── Invalid
              ↓
           Repair
              ↓
       Search additional venues
              ↓
           Re-plan
```

The workflow maintains state including:

- search count;
- repair iterations;
- retrieved venue candidates;
- weather metadata;
- validation state;
- current plan;
- trace ID;
- completion status.

Iteration limits prevent uncontrolled repair loops.

---

# 🧠 LLM Tool Calling

PlanPilot includes a structured agent controller that allows an LLM to reason over application tools instead of directly inventing planning facts.

The system separates responsibilities:

### LLM responsibilities

- natural-language interpretation;
- ambiguous intent resolution;
- structured tool selection;
- explanation generation.

### Deterministic software responsibilities

- budgets;
- travel calculations;
- constraint validation;
- route processing;
- opening-hours checks;
- scoring;
- plan ranking;
- repair limits.

This keeps language-model reasoning separate from factual constraint enforcement.

---

# 🔎 RAG + Vector Retrieval

PlanPilot includes a retrieval-augmented planning layer backed by **ChromaDB**.

Venue candidates can be embedded and retrieved semantically based on the user's request.

The retrieval layer supports:

- semantic venue recall;
- OpenAI embeddings when configured;
- deterministic embedding fallback for tests;
- Chroma vector storage;
- retrieval metadata;
- candidate ranking.

---

# 🎯 Hybrid Retrieval and Reranking

Pure vector similarity is not enough for itinerary planning.

PlanPilot therefore combines semantic retrieval with deterministic planning signals.

The reranker considers signals such as:

- semantic relevance;
- venue category;
- food preference match;
- vibe match;
- requested area;
- budget suitability;
- proximity to the starting location.

This creates explainable ranking rather than relying only on embedding similarity.

---

# 🌦️ Weather-Aware Replanning

PlanPilot integrates live weather information using **Open-Meteo**.

The weather layer can classify conditions as:

- low risk;
- moderate risk;
- high risk.

Weather metadata can influence planning constraints before venue retrieval and itinerary construction.

For example, outdoor activities can be deprioritized when conditions are unsuitable.

Weather failures are handled using fail-open behavior so temporary weather-provider problems do not prevent itinerary generation.

---

# 🔧 Agentic Repair Loop

If an itinerary fails validation, PlanPilot can attempt to repair the plan.

The repair workflow can:

1. inspect structured validation failures;
2. identify unsatisfied constraints;
3. search for additional venues;
4. rebuild the itinerary;
5. rerun validation;
6. stop when a usable plan is produced or the iteration limit is reached.

This turns PlanPilot from a single-pass recommendation engine into an iterative planning system.

---

# 🔌 Model Context Protocol — MCP

PlanPilot exposes capabilities through an **MCP server**.

Available MCP tools include:

- `parse_trip_request`
- `search_planpilot_places`
- `check_planpilot_weather`
- `plan_itinerary`

PlanPilot also exposes:

```text
planpilot://capabilities
```

Supported MCP transports include:

- stdio;
- streamable HTTP.

This allows external AI clients and agents to access PlanPilot as a tool provider.

---

# 📊 Evaluation Framework

PlanPilot contains an evaluation framework for measuring itinerary quality.

Current evaluation dimensions include:

- budget compliance;
- required-stop coverage;
- travel-constraint compliance;
- plan structure;
- hard-validation errors.

A weighted overall score is calculated from these metrics.

The repository includes benchmark cases under:

```text
evals/cases.json
```

## Current benchmark

On the current five-case benchmark:

| Planner | Cases Passed | Average Score |
|---|---:|---:|
| Baseline planner mode | 3 / 5 | 91.86% |
| LangGraph agentic mode | 5 / 5 | 100% |

The 100% result applies only to the current five-case development benchmark and should not be interpreted as universal production accuracy.

The benchmark is primarily designed to detect regressions and compare planning architectures as PlanPilot evolves.

---

# 🔭 Observability and Tracing

PlanPilot V2 includes native structured tracing for LangGraph executions.

Each graph run receives a unique:

```text
trace_id
```

Trace events record information such as:

- node name;
- execution duration;
- success or failure;
- search count;
- repair iteration count;
- current graph action;
- usable-plan status.

A graph trace can reveal where planning latency occurs across stages such as:

```text
weather
retrieval
planning
validation
repair
search
```

Development observability endpoints include:

```text
GET    /traces
GET    /traces/{trace_id}
DELETE /traces
```

The current trace store is intentionally in-memory and process-local.

---

# 🗺️ Example Production Result

For a request such as:

```text
Plan a chill rainy-day outing in Boston for two people under $150
with an activity, dinner and dessert.
```

PlanPilot can return alternatives such as:

```text
Best overall
Landmark Theatres
      ↓
The Bell in Hand
      ↓
Ben & Jerry
```

A generated plan can include:

- estimated group cost;
- total outing duration;
- travel time;
- live venue information;
- addresses;
- arrival times;
- opening-hours warnings;
- interactive map;
- route breakdown;
- ranking explanation.

PlanPilot explicitly surfaces uncertainty when live route or opening-hours information cannot be verified.

---

# 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │    Streamlit UI      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     FastAPI API      │
                         └──────────┬───────────┘
                                    │
                ┌───────────────────┴───────────────────┐
                │                                       │
                ▼                                       ▼
      Natural-Language Parser                 Structured Request
                │                                       │
                └───────────────────┬───────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Live Place Discovery │
                         │      Geoapify        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Hybrid RAG Retrieval │
                         │ Chroma + Reranking   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ LangGraph Workflow   │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
              Weather          Plan Builder       Validation
            Open-Meteo                              │
                                                    ▼
                                             Repair / Search
                                                    │
                                                    ▼
                                               Re-planning
                                                    │
                                                    ▼
                         ┌──────────────────────┐
                         │ Ranked Itineraries   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Map + Explanation    │
                         └──────────────────────┘
```

PlanPilot intentionally combines probabilistic AI components with deterministic planning logic.

---

# 🧰 Technology Stack

## AI / Agentic Systems

- OpenAI API
- LangGraph
- structured LLM outputs
- tool calling
- Retrieval-Augmented Generation
- semantic embeddings
- hybrid reranking
- Model Context Protocol
- agentic repair loops

## Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

## Retrieval

- ChromaDB
- semantic embeddings
- metadata-aware candidate retrieval
- deterministic reranking

## External APIs

- Geoapify Places API
- Geoapify routing
- Open-Meteo weather API
- OpenAI API

## Frontend

- Streamlit
- PyDeck
- Requests

## Testing / Evaluation

- pytest
- FastAPI TestClient
- HTTPX
- deterministic test providers
- benchmark evaluation framework

## Production

- Render — FastAPI backend
- Streamlit Community Cloud — frontend
- environment-based configuration
- production CORS configuration
- health checks

---

# 📁 Project Structure

```text
planpilot/
│
├── backend/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── models.py
│       ├── planner.py
│       ├── llm.py
│       │
│       ├── agent_controller.py
│       │
│       ├── graph_orchestrator.py
│       ├── graph_nodes.py
│       ├── graph_state.py
│       ├── graph_rag.py
│       ├── graph_weather.py
│       │
│       ├── rag_retriever.py
│       ├── reranker.py
│       │
│       ├── weather.py
│       ├── live_weather.py
│       ├── weather_policy.py
│       │
│       ├── evaluation.py
│       ├── eval_runner.py
│       ├── eval_cli.py
│       │
│       ├── observability.py
│       ├── observability_api.py
│       │
│       ├── mcp_server.py
│       │
│       └── tools/
│           ├── places.py
│           ├── live_candidates.py
│           ├── routing.py
│           └── opening_hours.py
│
├── frontend/
│   └── app.py
│
├── evals/
│   └── cases.json
│
├── tests/
│
├── .streamlit/
│   └── config.toml
│
├── .env.example
├── render.yaml
├── requirements.txt
├── pytest.ini
├── LICENSE
└── README.md
```

---

# 🚀 Production Deployment

## Live frontend

https://planpilot-ai.streamlit.app

Hosted using:

```text
Streamlit Community Cloud
```

## Live backend

https://planpilot-api.onrender.com

Hosted using:

```text
Render
```

Backend health:

```text
https://planpilot-api.onrender.com/health
```

The production deployment uses environment variables for API credentials and configuration.

Secrets are not stored in the repository.

---

# ⚙️ Local Development

## 1. Clone

```powershell
git clone https://github.com/saurya-koka/planpilot.git
cd planpilot
```

## 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Create `.env`

```powershell
Copy-Item .env.example .env
```

Configure values such as:

```env
PLANPILOT_ENV=development

GEOAPIFY_API_KEY=your_geoapify_key
PLACES_PROVIDER=geoapify

ROUTING_PROVIDER=geoapify
ROUTING_TIMEOUT_SECONDS=10

OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5

PLANPILOT_LIVE_WEATHER=true

BACKEND_URL=http://localhost:8000
```

Never commit the real `.env` file.

---

# ▶️ Running Locally

Start FastAPI:

```powershell
uvicorn backend.app.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Development API docs:

```text
http://localhost:8000/docs
```

Open another PowerShell terminal and activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start Streamlit:

```powershell
streamlit run frontend/app.py
```

Frontend:

```text
http://localhost:8501
```

---

# 🔗 Important API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | API status |
| `GET` | `/health` | Production/integration health |
| `POST` | `/plans` | Structured itinerary planning |
| `POST` | `/plan-from-text` | Natural-language planning |
| `POST` | `/plan-from-text/live/` | Natural-language planning with live venue data |
| `POST` | `/graph/plan-from-text` | LangGraph agentic planning |
| `GET` | `/traces` | List recent graph traces |
| `GET` | `/traces/{trace_id}` | Inspect a graph trace |
| `DELETE` | `/traces` | Clear development trace store |

Production API documentation is disabled by default.

---

# 🧪 Testing

Run the full suite:

```powershell
pytest -q --basetemp="$PWD\.pytest_tmp"
```

Current V2 regression result:

```text
260 passed
```

The suite covers areas including:

- API behavior;
- parsing;
- planning;
- live-place integration;
- routing;
- validation;
- agentic repair;
- LangGraph orchestration;
- RAG;
- hybrid reranking;
- weather-aware planning;
- MCP;
- evaluation;
- observability;
- production configuration;
- deployment files.

---

# 📈 V2 Development Milestones

| Milestone | Capability | Status |
|---|---|---|
| V2.1 | Real routing + route data | ✅ |
| V2.2 | Interactive itinerary map | ✅ |
| V2.3 | Structured validation failures | ✅ |
| V2.4 | Agentic repair loop | ✅ |
| V2.5 | LLM structured outputs + tools | ✅ |
| V2.6 | LangGraph orchestration | ✅ |
| V2.7 | RAG + vector database | ✅ |
| V2.8 | Hybrid retrieval + reranking | ✅ |
| V2.9 | Weather-aware replanning | ✅ |
| V2.10 | MCP integration | ✅ |
| V2.11 | Evaluation framework | ✅ |
| V2.12 | Tracing + observability | ✅ |
| V2.13 | Production deployment | ✅ |

---

# ⚠️ Production Notes

PlanPilot intentionally exposes uncertainty instead of silently fabricating precision.

A generated itinerary may therefore contain warnings when:

- a routing provider fails and an estimated route is used;
- opening hours cannot be verified;
- an external API is temporarily unavailable;
- a venue lacks complete live metadata.

The free Render backend may also experience cold-start latency after periods of inactivity.

The current observability trace store is in-memory and is intended primarily for development and debugging.

Evaluation scores represent the included development benchmark and are not claims of universal real-world accuracy.

---

# 🔐 Security

Real API keys must never be committed to GitHub.

Production credentials are configured through:

- Render environment variables;
- Streamlit Community Cloud secrets.

Files such as `.env` and local persistent data are excluded through `.gitignore`.

---

# 🧠 Engineering Philosophy

PlanPilot follows a simple principle:

> **Use language models for ambiguity and reasoning. Use deterministic software for facts, constraints, validation, calculations, and safety-critical decisions.**

The goal is not to make an LLM generate an itinerary by itself.

The goal is to build an AI system in which language models, tools, retrieval, validation, live APIs, and deterministic software work together.

---

# 👨‍💻 Author

**Saurya Koka**

GitHub: https://github.com/saurya-koka

Project:

https://github.com/saurya-koka/planpilot
