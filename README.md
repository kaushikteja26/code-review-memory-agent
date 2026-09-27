# AI Code Review Agent with Persistent Memory

> **HackwithHyderabad 3.0 — PS #8: Code Review Agent**

An AI-powered code review agent that **learns your team's specific coding standards, conventions, and review patterns** over time through **persistent Hindsight memory by Vectorize**.

## Key Innovation

Traditional AI code reviewers give generic feedback. Our agent:
- **Remembers** previous review decisions, team conventions, and recurring issues
- **Retrieves** relevant team knowledge for each new PR using semantic search
- **Applies** learned patterns to produce team-specific reviews
- **Learns** from each review, getting better over time

**Without Memory → Generic review**
**With Memory → Team-specific review citing learned conventions**

## Architecture

```
GitHub PR URL → Fetch Diff → Ruff Analysis → Hindsight Memory → LLM Review → Structured Output
                                                  ↑                              ↓
                                            Team Knowledge ← ← ← ← ← ← Extract Learnings
```

## Quick Start

### 1. Setup

```bash
cd mp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your API keys:
# - LLM_PROVIDER=google (or groq)
# - GOOGLE_API_KEY (required for default provider) — https://aistudio.google.com/app/apikey
# - GROQ_API_KEY (if using groq) — https://console.groq.com
# - HINDSIGHT_API_KEY (required) — https://ui.hindsight.vectorize.io
# - GITHUB_TOKEN (optional) — for real PR reviews
```

### 3. Run

```bash
uvicorn app:app --reload
# Open http://localhost:8000
```

### 4. Demo

In the web UI:
1. Click **"Step 1: Review WITHOUT Memory"** — see generic feedback
2. Click **"Step 2: Seed Team Knowledge"** — load 10 team conventions into Hindsight
3. Click **"Step 3: Review WITH Memory"** — see team-specific feedback with memory references

Or type `demo` in the PR input box to review the built-in synthetic PR.

## Project Structure

```
mp/
├── app.py                     # FastAPI web application
├── config.py                  # Environment configuration
├── core/
│   ├── models.py              # Pydantic data models
│   ├── orchestrator.py        # Main review pipeline
│   └── prompts.py             # LLM prompt templates
├── github_client/
│   └── client.py              # GitHub API integration
├── analyzer/
│   └── static_analysis.py     # Ruff integration
├── memory/
│   └── hindsight_manager.py   # Hindsight abstraction layer
├── llm/
│   └── reviewer.py            # LLM integration (Google Gemini / Groq)
├── demo/
│   ├── seed_memories.py       # Historical team knowledge
│   ├── sample_diffs.py        # Synthetic PR diffs
│   └── run_demo.py            # CLI before/after demo
├── templates/
│   └── index.html             # Web UI
└── static/
    └── style.css              # Styles
```

## How Hindsight Memory Works

### Memory Operations
- **Retain** — Store structured team knowledge (conventions, decisions, patterns)
- **Recall** — Semantic search for relevant memories based on PR context
- **Reflect** — Synthesize insights from stored memories

### Memory Types
| Type | Example |
|------|---------|
| Team Convention | "Use repository pattern, no direct DB in routes" |
| Architectural Decision | "All external calls must be async" |
| Recurring Issue | "Developers often forget type hints" |
| Review Feedback | "Error responses must use AppError wrapper" |

### Smart Query Building
The agent analyzes each PR's diff to build targeted memory queries:
- Detects database code → queries for DB access patterns
- Detects API routes → queries for endpoint conventions
- Detects external calls → queries for async patterns
- Always queries for general team conventions

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI + Jinja2 |
| GitHub API | PyGithub |
| Memory | Hindsight by Vectorize |
| LLM | Google Gemini (AI Studio), Groq supported |
| Static Analysis | Ruff |
| Data Models | Pydantic v2 |

## Demo Flow

1. **WITHOUT MEMORY**: Agent gives standard Python best practices feedback
2. **SEED KNOWLEDGE**: 10 team-specific conventions loaded into Hindsight
3. **WITH MEMORY**: Agent identifies violations of team conventions and explicitly cites which convention was violated and where it was learned

The "MEMORY USED" panel shows exactly how many memories were retrieved and matched.

## Team

Built for HackwithHyderabad 3.0

---

*Powered by [Hindsight by Vectorize](https://hindsight.vectorize.io) — Persistent Memory for AI Agents*
