"""
Adaptive Learning Engine – FastAPI entry point.

Endpoints:
  POST /start          – begin a new learning session for a topic
  POST /answer         – submit the learner's answer and advance the graph
  POST /upload_pdf     – ingest a PDF into the FAISS vector store
  GET  /state/{user_id} – inspect full session state
"""

import json
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph.builder import get_graph, get_thread_config
from memory.profile_store import get_profile
from models.state import make_default_state
from rag.pdf_ingest import ingest_pdf
from utils.config import validate_config


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()
    # Pre-initialise the graph so first request is not slow
    get_graph()
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Adaptive Learning Engine",
    description="Stateful, graph-driven adaptive tutor with misconception tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class StartRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="Unique learner identifier")
    topic: str = Field(..., min_length=1, description="Topic to study")


class AnswerRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    user_answer: str = Field(..., min_length=1, description="Learner's answer to the current question")


class StartResponse(BaseModel):
    status: str
    user_id: str
    topic: str
    explanation: Dict[str, Any]
    question: Dict[str, Any]
    attempts: int


class AnswerResponse(BaseModel):
    status: str
    user_id: str
    evaluation: Dict[str, Any]
    misconceptions: list
    feedback: Optional[Dict[str, Any]]
    learning_profile: Dict[str, Any]
    next_action: str
    attempts: int
    question: Optional[Dict[str, Any]] = None
    explanation: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_field(raw: str, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _extract_feedback(chat_history: list) -> Optional[Dict[str, Any]]:
    """Return metadata of the most recent feedback message."""
    for entry in reversed(chat_history):
        if isinstance(entry, dict) and entry.get("type") == "feedback":
            return entry.get("metadata")
    return None


def _current_state_values(user_id: str) -> Dict[str, Any]:
    graph = get_graph()
    config = get_thread_config(user_id)
    snapshot = graph.get_state(config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail=f"No active session for user '{user_id}'")
    return snapshot.values


# ---------------------------------------------------------------------------
# POST /start
# ---------------------------------------------------------------------------

@app.post("/start", response_model=StartResponse)
async def start_session(req: StartRequest) -> StartResponse:
    """
    Initialise a new learning session.

    Runs: context_builder → explain_node → ask_node
    Then interrupts and returns the explanation + first question.
    """
    graph = get_graph()
    config = get_thread_config(req.user_id)

    # Build initial state; merge existing profile if user has history
    profile = get_profile(req.user_id)
    initial_state = make_default_state(req.user_id, req.topic)
    initial_state["learning_profile"] = profile

    # Run the graph until the first interrupt (after ask_node)
    graph.invoke(initial_state, config)

    # Read the paused state
    values = _current_state_values(req.user_id)

    explanation = _parse_json_field(values.get("current_explanation", ""), {})
    question = _parse_json_field(values.get("current_question", ""), {})

    return StartResponse(
        status="waiting_for_answer",
        user_id=req.user_id,
        topic=req.topic,
        explanation=explanation,
        question=question,
        attempts=values.get("attempts", 0),
    )


# ---------------------------------------------------------------------------
# POST /answer
# ---------------------------------------------------------------------------

@app.post("/answer", response_model=AnswerResponse)
async def submit_answer(req: AnswerRequest) -> AnswerResponse:
    """
    Submit the learner's answer.

    Resumes graph: evaluate_node → misconception_node → feedback_node → router_node
    If router chooses followup/simplify the graph continues to the next ask_node
    interrupt automatically before returning.
    """
    graph = get_graph()
    config = get_thread_config(req.user_id)

    # Verify an active session exists
    snapshot = graph.get_state(config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"No active session for user '{req.user_id}'. Call POST /start first.",
        )

    # Inject the learner's answer into the paused state
    graph.update_state(config, {"user_answer": req.user_answer})

    # Resume execution (runs evaluate → misconception → feedback → router,
    # then optionally ask_node again if followup/simplify)
    graph.invoke(None, config)

    # Read final/interrupted state
    values = _current_state_values(req.user_id)
    final_snapshot = graph.get_state(config)

    next_action: str = values.get("next_action", "followup")
    is_interrupted: bool = bool(final_snapshot.next)  # True = waiting for another answer

    # Common fields
    response_data: Dict[str, Any] = {
        "status": "waiting_for_answer" if is_interrupted else "session_complete",
        "user_id": req.user_id,
        "evaluation": values.get("evaluation", {}),
        "misconceptions": values.get("misconceptions", []),
        "feedback": _extract_feedback(values.get("chat_history", [])),
        "learning_profile": values.get("learning_profile", {}),
        "next_action": next_action,
        "attempts": values.get("attempts", 0),
    }

    # Append question (and explanation on simplify) when still active
    if is_interrupted:
        response_data["question"] = _parse_json_field(
            values.get("current_question", ""), {}
        )
        if next_action == "simplify":
            response_data["explanation"] = _parse_json_field(
                values.get("current_explanation", ""), {}
            )

    return AnswerResponse(**response_data)


# ---------------------------------------------------------------------------
# POST /upload_pdf
# ---------------------------------------------------------------------------

@app.post("/upload_pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    topic: str = Form(...),
) -> Dict[str, Any]:
    """
    Ingest a PDF into the FAISS vector store, tagged with the given topic.
    The chunks become available for context_builder retrieval immediately.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    chunks_stored, total_chars = ingest_pdf(
        file_bytes=file_bytes,
        topic=topic,
        filename=file.filename,
    )

    if chunks_stored == 0:
        raise HTTPException(
            status_code=422,
            detail="Could not extract any text from the PDF. "
            "Ensure the file is not scanned or image-only.",
        )

    return {
        "status": "ingested",
        "filename": file.filename,
        "topic": topic,
        "chunks_stored": chunks_stored,
        "total_characters": total_chars,
    }


# ---------------------------------------------------------------------------
# GET /state/{user_id}
# ---------------------------------------------------------------------------

@app.get("/state/{user_id}")
async def get_session_state(user_id: str) -> Dict[str, Any]:
    """
    Return the full session state for inspection / debugging.
    """
    values = _current_state_values(user_id)

    # Parse JSON-encoded fields for clean output
    explanation = _parse_json_field(values.get("current_explanation", ""), {})
    question = _parse_json_field(values.get("current_question", ""), {})

    return {
        "user_id": user_id,
        "topic": values.get("topic", ""),
        "attempts": values.get("attempts", 0),
        "next_action": values.get("next_action", ""),
        "current_explanation": explanation,
        "current_question": question,
        "evaluation": values.get("evaluation", {}),
        "misconceptions": values.get("misconceptions", []),
        "learning_profile": values.get("learning_profile", {}),
        "retrieved_context_count": len(values.get("retrieved_context", [])),
        "chat_history_length": len(values.get("chat_history", [])),
        "chat_history": values.get("chat_history", []),
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}
