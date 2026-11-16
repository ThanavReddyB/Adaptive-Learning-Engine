# Adaptive Learning Engine

This project is a full-stack adaptive tutoring system:

- The backend is a FastAPI app powered by a LangGraph state machine.
- The frontend is a Streamlit chat UI.
- Learning is personalized using:
  - LLM-generated explanations/questions/evaluations,
  - misconception detection,
  - an in-memory learner profile,
  - retrieval from a FAISS vecgtor store (PDF chunks + prior generated content),
  - optional Tavily web fallback when local context is thin.

## End-to-End Flow

1. User starts a session with a topic.
2. Backend graph runs:
   - `context_builder` retrieves topic context from vector store (+ optional Tavily).
   - `explain_node` creates simple/normal/deep explanation JSON.
   - `ask_node` creates a conceptual question JSON.
3. Graph interrupts after `ask_node` and waits for user answer.
4. User submits an answer.
5. Backend resumes graph:
   - `evaluate_node` scores/labels the answer,
   - `misconception_node` detects conceptual errors,
   - `feedback_node` generates targeted feedback and updates learner profile,
   - `router_node` chooses `advance`, `followup`, or `simplify`.
6. If `followup` or `simplify`, graph cycles and pauses again after next question.
7. If `advance` (or max attempts reached), session completes.

## Project Structure

### Root

- `README.md`
  - This documentation file.

---

## backend/

- `main.py`
  - FastAPI entrypoint.
  - Validates environment config on startup (`validate_config`) and prebuilds the graph (`get_graph`).
  - Exposes API endpoints:
    - `POST /start`: creates default state, loads prior profile, runs graph until first interrupt, returns explanation + first question.
    - `POST /answer`: injects user answer into paused graph, resumes, returns evaluation/misconceptions/feedback and next question if still active.
    - `POST /upload_pdf`: extracts/chunks/indexes uploaded PDF into vector store.
    - `GET /state/{user_id}`: debugging endpoint returning full current state.
    - `GET /health`: simple health check.
  - Handles JSON parsing of graph fields and response shaping via Pydantic models.

- `requirements.txt`
  - Backend dependencies:
    - API: FastAPI, Uvicorn, multipart upload support.
    - Orchestration: LangGraph/LangChain core.
    - LLM provider client: OpenAI SDK (used with OpenRouter base URL).
    - Retrieval: FAISS + NumPy + sentence-transformers.
    - External search: Tavily.
    - PDF parsing: pdfplumber.
    - Config and validation: python-dotenv, pydantic.

- `.env` (local, not shown in the tree above but used)
  - Holds required API keys and optional runtime overrides:
    - `OR_KEY`, `TAVILY_API_KEY` required.
    - `DEFAULT_MODEL`, `EMBEDDING_MODEL`, `MAX_ATTEMPTS`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`, `MIN_CONTEXT_CHARS` optional.

### backend/graph/

- `graph/builder.py`
  - Builds and compiles the LangGraph state machine.
  - Registers all nodes and edges (linear + conditional router edges).
  - Configures `interrupt_after=["ask_node"]` so the graph pauses waiting for learner input.
  - Uses a process-wide `MemorySaver` checkpointer.
  - Exposes:
    - `get_graph()` lazy singleton accessor.
    - `get_thread_config(user_id)` so each learner has isolated thread state.

- `graph/nodes.py`
  - Implements all seven graph nodes and helper JSON parsing:
    - `context_builder`: retrieves vector context and falls back to Tavily search if insufficient.
    - `explain_node`: creates multi-depth explanation JSON and stores normal explanation in vector DB.
    - `ask_node`: creates adaptive conceptual question JSON (difficulty depends on attempts/profile).
    - `evaluate_node`: scores answer, normalizes label, stores answer in vector DB.
    - `misconception_node`: extracts misconception objects, filters low confidence, stores them in vector DB.
    - `feedback_node`: generates personalized feedback and updates learner profile.
    - `router_node`: increments attempts and decides `advance`/`followup`/`simplify` with max-attempt safety.

- `graph/router.py`
  - Defines canonical route labels (`advance`, `followup`, `simplify`).
  - Provides `route_from_router_node(state)` used by LangGraph conditional edges.

- `graph/__init__.py`
  - Empty package marker for Python imports.

### backend/memory/

- `memory/profile_store.py`
  - In-memory user profile storage keyed by `user_id`.
  - Tracks strengths, weak areas, and per-topic progress (attempts, scores, average, last label).
  - Adds misconception-derived weak-area tags (`topic::misconception_type`) for high-confidence errors.
  - Exposes profile read/update/reset utilities.

- `memory/vector_store.py`
  - In-memory FAISS vector index wrapper.
  - Supports single and batch add operations with metadata.
  - Supports semantic search with optional topic/type filters.
  - Returns ranked docs with distances.
  - Exposes singleton accessor `get_vector_store()`.

- `memory/__init__.py`
  - Empty package marker.

### backend/models/

- `models/state.py`
  - Defines all typed state objects (`EvaluationResult`, `Misconception`, `LearningProfile`, `LearningState`).
  - `LearningState` is the shared LangGraph state contract.
  - Uses `Annotated[..., operator.add]` for `chat_history` so node outputs append across steps.
  - Provides `make_default_state(user_id, topic)` for session initialization.

- `models/__init__.py`
  - Empty package marker.

### backend/prompts/

- `prompts/explain.py`
  - System prompt and prompt-builder for multi-depth explanation generation.
  - Enforces strict JSON schema with `simple`, `normal`, `deep`, `key_concepts`, `common_pitfalls`.
  - Supports simplification mode when learner is struggling.

- `prompts/ask.py`
  - System prompt and builder for conceptual question generation.
  - Enforces JSON schema containing question, type, difficulty, hint, expected concepts, avoid keywords.
  - Difficulty target escalates by attempt count.

- `prompts/evaluate.py`
  - System prompt and builder for answer grading.
  - Enforces JSON schema for score, label, reasoning, and correct/missing/incorrect elements.
  - Includes explicit scoring rubric bands.

- `prompts/misconception.py`
  - System prompt and builder for misconception extraction.
  - Enforces JSON array output with categorized misconception objects and confidence.
  - Focuses on incorrect statements (not just omissions).

- `prompts/feedback.py`
  - System prompt and builder for personalized formative feedback.
  - Enforces JSON feedback schema and tone rules based on score band.
  - Uses evaluation + misconception + profile context to create next-step guidance.

- `prompts/__init__.py`
  - Empty package marker.

### backend/rag/

- `rag/pdf_ingest.py`
  - PDF ingestion pipeline:
    - extract text with `pdfplumber`,
    - split into overlapping word chunks,
    - embed and store chunks in vector DB with metadata (`topic`, `source`, `chunk_index`).
  - Returns ingestion stats (`chunks_stored`, `total_characters`).

- `rag/tavily_client.py`
  - Wraps Tavily search client with lazy initialization.
  - Normalizes web results into internal format (`source`, `content`, `url`, `score`).
  - Adds Tavily synthesized answer as top context item when present.
  - Provides `is_context_sufficient()` threshold check using `MIN_CONTEXT_CHARS`.

- `rag/__init__.py`
  - Empty package marker.

### backend/utils/

- `utils/config.py`
  - Loads environment variables from `.env`.
  - Defines config constants (keys, model names, vector dim, retries, limits).
  - Provides `validate_config()` that raises at startup if required keys are missing.

- `utils/embeddings.py`
  - Lazy-loads sentence-transformers embedding model.
  - Provides `embed_texts` and `embed_text` utilities.
  - Returns `float32` vectors for FAISS compatibility.

- `utils/llm.py`
  - OpenRouter-backed LLM client wrapper (via OpenAI-compatible SDK).
  - `call_llm`: robust text call with retry/backoff for timeout/rate/API failures.
  - `_extract_json`: strips code fences and trims leading prose.
  - `call_llm_json`: repeatedly requests parseable JSON with corrective retry prompting.

- `utils/__init__.py`
  - Empty package marker.

---

## frontend/

- `frontend/app.py`
  - Streamlit chat frontend for the tutor.
  - Handles session state initialization (`user_id`, messages, flags, profile snapshot).
  - Defines backend API wrappers:
    - `api_start(topic)`
    - `api_answer(answer)`
    - `api_upload_pdf(data, name, topic)`
  - Rendering helpers:
    - explanation cards by depth,
    - question display (type/difficulty/hint),
    - evaluation badge, misconception cards, feedback card.
  - Sidebar controls:
    - explanation depth selector,
    - new session reset,
    - PDF upload and topic tagging,
    - profile/progress display and attempt bar.
  - Main chat behavior:
    - first input starts session (topic),
    - next inputs are learner answers,
    - adapts display based on backend `next_action` and completion status.
  - Includes extensive custom CSS for modern UI styling.

---

## Operational Notes

- Data persistence is currently in-memory only:
  - profiles and vector index reset when backend restarts.
- One graph thread per `user_id`:
  - session continuity depends on sending the same `user_id`.
- `MAX_ATTEMPTS` safety cap prevents infinite remediation loops.
- Frontend and backend should agree on backend URL and attempt limit behavior.

## How to Run

1. Backend
   - `cd backend`
   - `pip install -r requirements.txt`
   - ensure `.env` contains required keys
   - `uvicorn main:app --reload --port 8000`
2. Frontend (new terminal)
   - `cd frontend`
   - `pip install streamlit requests`
   - `streamlit run app.py`
