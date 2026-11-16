# Adaptive Learning Engine

An AI-powered adaptive tutoring system that personalizes learning through real-time misconception detection, formative feedback, and intelligent question routing. Built with LangGraph, FastAPI, and Streamlit.

## Features

- **Adaptive question routing** — scores each answer and decides whether to advance, follow up, or simplify the explanation
- **Misconception detection** — identifies specific conceptual errors with confidence scores and targeted corrections
- **Multi-depth explanations** — generates simple, standard, and deep-dive explanations for every topic
- **Learner profiling** — tracks strengths, weak areas, and per-topic progress across sessions
- **RAG-augmented context** — retrieves relevant content from uploaded PDFs via FAISS, with Tavily web search as fallback
- **PDF ingestion** — upload reference material that immediately becomes available for context retrieval

## Architecture

```
┌─────────────┐         ┌──────────────────────────────────────────────────┐
│  Streamlit   │  HTTP   │  FastAPI Backend                                 │
│  Frontend    │◄───────►│                                                  │
│              │         │  ┌──────────────────────────────────────────┐    │
│  • Chat UI   │         │  │  LangGraph State Machine                 │    │
│  • PDF upload│         │  │                                          │    │
│  • Profile   │         │  │  context_builder ──► explain_node        │    │
│    display   │         │  │       │                   │               │    │
│              │         │  │       ▼                   ▼               │    │
│              │         │  │  ┌─────────┐        ask_node ◄──┐       │    │
│              │         │  │  │  FAISS   │          │  PAUSE  │       │    │
│              │         │  │  │  Vector  │          ▼         │       │    │
│              │         │  │  │  Store   │    evaluate_node   │       │    │
│              │         │  │  └─────────┘          │         │       │    │
│              │         │  │       ▲          misconception   │       │    │
│              │         │  │       │            _node         │       │    │
│              │         │  │   Tavily Web          │         │       │    │
│              │         │  │   (fallback)    feedback_node   │       │    │
│              │         │  │                       │         │       │    │
│              │         │  │                  router_node     │       │    │
│              │         │  │                 /     |     \    │       │    │
│              │         │  │            advance followup simplify    │    │
│              │         │  │              │      └───────┴───►│       │    │
│              │         │  │              ▼                    │       │    │
│              │         │  │             END                   │       │    │
│              │         │  └──────────────────────────────────────────┘    │
│              │         │                                                  │
└─────────────┘         └──────────────────────────────────────────────────┘
                                          │
                                          ▼
                                   OpenRouter API
                                  (Llama 3.3 70B)
```

## Quick Start

### Prerequisites

- Python 3.12+
- An [OpenRouter](https://openrouter.ai/) API key
- A [Tavily](https://tavily.com/) API key

### 1. Clone and install

```bash
git clone <repo-url>
cd LLM_JF
pip install -r backend/requirements.txt
pip install streamlit requests
```

### 2. Configure environment

Create `backend/.env`:

```env
OR_KEY=your_openrouter_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Optional overrides:

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_MODEL` | `meta-llama/llama-3.3-70b-instruct` | LLM model via OpenRouter |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |
| `MAX_ATTEMPTS` | `5` | Max questions before forcing topic advancement |
| `LLM_TIMEOUT` | `90` | LLM request timeout in seconds |
| `LLM_MAX_RETRIES` | `3` | Retry count for failed LLM calls |
| `MIN_CONTEXT_CHARS` | `300` | Minimum retrieved context before triggering web search |

### 3. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Start the frontend (new terminal)

```bash
cd frontend
streamlit run app.py
```

The app opens at `http://localhost:8501`. Type a topic to begin.

## How It Works

**Starting a session:** The user enters a topic. The backend retrieves context from the vector store (falling back to Tavily web search if local context is thin), generates a three-level explanation, and poses an adaptive question. The graph pauses and waits for the learner's answer.

**Answering:** The learner submits an answer. The backend scores it (0–100%), detects misconceptions, generates personalized feedback, and updates the learner profile. A router then decides the next step:

| Score | Action | What happens |
|---|---|---|
| > 80% | **Advance** | Topic mastered — session completes |
| 40–80% | **Follow up** | New question on the same topic |
| < 40% | **Simplify** | Re-explain with simpler language, then ask again |

After `MAX_ATTEMPTS` questions, the session advances regardless of score.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/start` | Begin a new learning session for a topic |
| `POST` | `/answer` | Submit the learner's answer and advance the graph |
| `POST` | `/upload_pdf` | Ingest a PDF into the vector store |
| `GET` | `/state/{user_id}` | Inspect full session state (debug) |
| `GET` | `/health` | Health check |

<details>
<summary><strong>POST /start</strong></summary>

**Request:**
```json
{
  "user_id": "alice",
  "topic": "binary search trees"
}
```

**Response:**
```json
{
  "status": "waiting_for_answer",
  "user_id": "alice",
  "topic": "binary search trees",
  "explanation": {
    "simple": "...",
    "normal": "...",
    "deep": "...",
    "key_concepts": ["..."],
    "common_pitfalls": ["..."]
  },
  "question": {
    "question": "...",
    "question_type": "conceptual",
    "difficulty": "medium",
    "hint": "...",
    "expected_concepts": ["..."]
  },
  "attempts": 0
}
```
</details>

<details>
<summary><strong>POST /answer</strong></summary>

**Request:**
```json
{
  "user_id": "alice",
  "user_answer": "A BST maintains sorted order by..."
}
```

**Response:**
```json
{
  "status": "waiting_for_answer",
  "user_id": "alice",
  "evaluation": {
    "score": 0.65,
    "label": "partial",
    "reasoning": "...",
    "correct_elements": ["..."],
    "missing_elements": ["..."],
    "incorrect_elements": ["..."]
  },
  "misconceptions": [
    {
      "type": "overgeneralization",
      "description": "...",
      "confidence": 0.85,
      "correction": "..."
    }
  ],
  "feedback": {
    "message": "...",
    "reinforcements": ["..."],
    "improvements": ["..."],
    "learning_guidance": ["..."],
    "next_steps": ["..."]
  },
  "learning_profile": { "..." },
  "next_action": "followup",
  "attempts": 1,
  "question": { "..." }
}
```
</details>

<details>
<summary><strong>POST /upload_pdf</strong></summary>

**Request:** multipart form — `file` (PDF) + `topic` (string)

**Response:**
```json
{
  "status": "ingested",
  "filename": "textbook_ch3.pdf",
  "topic": "binary search trees",
  "chunks_stored": 42,
  "total_characters": 28750
}
```
</details>

## Project Structure

```
backend/
├── main.py                  # FastAPI app and endpoint definitions
├── requirements.txt         # Python dependencies
├── .env                     # API keys and config overrides
├── graph/
│   ├── builder.py           # LangGraph state machine construction
│   ├── nodes.py             # All 7 graph nodes (context → explain → ask → evaluate → misconception → feedback → router)
│   └── router.py            # Conditional routing logic (advance / followup / simplify)
├── memory/
│   ├── profile_store.py     # In-memory learner profile storage
│   └── vector_store.py      # FAISS vector index wrapper
├── models/
│   └── state.py             # Typed state definitions (LearningState, EvaluationResult, etc.)
├── prompts/
│   ├── explain.py           # Multi-depth explanation generation prompts
│   ├── ask.py               # Adaptive question generation prompts
│   ├── evaluate.py          # Answer evaluation and scoring prompts
│   ├── misconception.py     # Misconception extraction prompts
│   └── feedback.py          # Personalized feedback generation prompts
├── rag/
│   ├── pdf_ingest.py        # PDF text extraction and chunking pipeline
│   └── tavily_client.py     # Tavily web search fallback
└── utils/
    ├── config.py            # Environment variable loading and validation
    ├── embeddings.py        # Sentence-transformers embedding utilities
    └── llm.py               # OpenRouter LLM client with retry and JSON extraction

frontend/
└── app.py                   # Streamlit chat UI
```

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Llama 3.3 70B via [OpenRouter](https://openrouter.ai/) |
| Orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) state machine with interrupt-based control flow |
| Embeddings | [sentence-transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`) |
| Vector search | [FAISS](https://github.com/facebookresearch/faiss) (in-memory, L2 distance) |
| Web search | [Tavily](https://tavily.com/) (fallback when local context is insufficient) |
| Backend | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Frontend | [Streamlit](https://streamlit.io/) |

## Limitations

- **In-memory only** — learner profiles and the vector index reset when the backend restarts. There is no persistent database.
- **Single-process** — the FAISS index and profile store are process-level singletons, so horizontal scaling requires a shared store.
- **No authentication** — session continuity depends on sending the same `user_id`. Anyone can query any user's state.
