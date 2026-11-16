"""
All seven LangGraph nodes for the Adaptive Learning Engine.

Node execution order:
  START → context_builder → explain_node → ask_node
        → [INTERRUPT – wait for user_answer]
        → evaluate_node → misconception_node → feedback_node → router_node
        → (advance → END | followup → ask_node | simplify → explain_node)
"""

import json
from typing import Any, Dict

from memory.profile_store import get_profile, update_profile
from memory.vector_store import get_vector_store
from models.state import LearningState
from prompts.ask import ASK_SYSTEM_PROMPT, build_ask_prompt
from prompts.evaluate import EVALUATE_SYSTEM_PROMPT, build_evaluate_prompt
from prompts.explain import EXPLAIN_SYSTEM_PROMPT, build_explain_prompt
from prompts.feedback import FEEDBACK_SYSTEM_PROMPT, build_feedback_prompt
from prompts.misconception import MISCONCEPTION_SYSTEM_PROMPT, build_misconception_prompt
from rag.tavily_client import is_context_sufficient, search_web
from utils.config import MAX_ATTEMPTS
from utils.llm import call_llm_json


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_parse_json(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _question_text(state: LearningState) -> str:
    qdata = _safe_parse_json(state.get("current_question", ""), {})
    return qdata.get("question", state.get("current_question", ""))


def _explanation_normal(state: LearningState) -> str:
    edata = _safe_parse_json(state.get("current_explanation", ""), {})
    return edata.get("normal", state.get("current_explanation", ""))


# ---------------------------------------------------------------------------
# Node 1 – context_builder
# ---------------------------------------------------------------------------

def context_builder(state: LearningState) -> Dict[str, Any]:
    """
    Retrieve relevant context from the FAISS vector store.
    Fall back to Tavily web search when stored context is insufficient.
    """
    topic: str = state["topic"]

    store = get_vector_store()
    vector_hits = store.search(query=topic, k=6, filter_topic=topic)
    context: list = [hit["text"] for hit in vector_hits if hit.get("text")]

    if not is_context_sufficient(context):
        web_hits = search_web(f"{topic} explanation concepts")
        web_texts = [r["content"] for r in web_hits if r.get("content")]
        context.extend(web_texts[:4])

    return {"retrieved_context": context}


# ---------------------------------------------------------------------------
# Node 2 – explain_node
# ---------------------------------------------------------------------------

def explain_node(state: LearningState) -> Dict[str, Any]:
    """
    Generate a three-level explanation (simple / normal / deep).
    Detects whether this is a simplification re-run and adjusts accordingly.
    """
    topic: str = state["topic"]
    context: list = state.get("retrieved_context", [])
    profile = get_profile(state["user_id"])
    simplify: bool = state.get("next_action") == "simplify"

    user_prompt = build_explain_prompt(topic, context, profile, simplify=simplify)
    explanation: dict = call_llm_json(EXPLAIN_SYSTEM_PROMPT, user_prompt)

    # Persist the normal explanation to vector store so future sessions benefit
    store = get_vector_store()
    store.add(
        text=explanation.get("normal", ""),
        metadata={
            "topic": topic,
            "type": "explanation",
            "user_id": state["user_id"],
        },
    )

    chat_entry = {
        "role": "assistant",
        "type": "explanation",
        "content": explanation.get("normal", ""),
        "metadata": explanation,
    }

    return {
        "current_explanation": json.dumps(explanation),
        "chat_history": [chat_entry],
    }


# ---------------------------------------------------------------------------
# Node 3 – ask_node
# ---------------------------------------------------------------------------

def ask_node(state: LearningState) -> Dict[str, Any]:
    """
    Generate a conceptual (non-memorisation) question based on the explanation.
    Difficulty escalates with attempt count.
    """
    topic: str = state["topic"]
    attempts: int = state.get("attempts", 0)
    profile = get_profile(state["user_id"])
    explanation: dict = _safe_parse_json(state.get("current_explanation", ""), {})

    user_prompt = build_ask_prompt(topic, explanation, profile, attempts)
    question_data: dict = call_llm_json(ASK_SYSTEM_PROMPT, user_prompt)

    chat_entry = {
        "role": "assistant",
        "type": "question",
        "content": question_data.get("question", ""),
        "metadata": question_data,
    }

    return {
        "current_question": json.dumps(question_data),
        "chat_history": [chat_entry],
    }


# ---------------------------------------------------------------------------
# Node 4 – evaluate_node
# ---------------------------------------------------------------------------

def evaluate_node(state: LearningState) -> Dict[str, Any]:
    """
    Score the learner's answer and classify it as correct / partial / incorrect.
    Stores the raw answer in the vector store.
    """
    topic: str = state["topic"]
    user_answer: str = state.get("user_answer", "")

    question_data: dict = _safe_parse_json(state.get("current_question", ""), {})
    question_text: str = question_data.get("question", _question_text(state))
    expected_concepts: list = question_data.get("expected_concepts", [])
    explanation_given: str = _explanation_normal(state)

    user_prompt = build_evaluate_prompt(
        question_text, user_answer, expected_concepts, topic, explanation_given
    )
    evaluation: dict = call_llm_json(EVALUATE_SYSTEM_PROMPT, user_prompt)

    # Normalise score and label
    score: float = max(0.0, min(1.0, float(evaluation.get("score", 0.0))))
    if score >= 0.8:
        label = "correct"
    elif score >= 0.4:
        label = "partial"
    else:
        label = "incorrect"

    evaluation["score"] = score
    evaluation["label"] = label
    evaluation.setdefault("correct_elements", [])
    evaluation.setdefault("missing_elements", [])
    evaluation.setdefault("incorrect_elements", [])

    # Store answer for future similarity retrieval
    store = get_vector_store()
    store.add(
        text=user_answer,
        metadata={
            "topic": topic,
            "type": "user_answer",
            "user_id": state["user_id"],
            "score": score,
            "label": label,
        },
    )

    chat_entry = {
        "role": "user",
        "type": "answer",
        "content": user_answer,
        "metadata": {"evaluation": evaluation},
    }

    return {
        "evaluation": evaluation,
        "chat_history": [chat_entry],
    }


# ---------------------------------------------------------------------------
# Node 5 – misconception_node
# ---------------------------------------------------------------------------

def misconception_node(state: LearningState) -> Dict[str, Any]:
    """
    Identify specific conceptual errors in the learner's answer.
    Stores each misconception in the vector store for longitudinal tracking.
    """
    topic: str = state["topic"]
    user_answer: str = state.get("user_answer", "")
    evaluation: dict = state.get("evaluation", {})
    question_text: str = _question_text(state)

    user_prompt = build_misconception_prompt(user_answer, evaluation, topic, question_text)
    raw = call_llm_json(MISCONCEPTION_SYSTEM_PROMPT, user_prompt)

    # Ensure we always have a list
    misconceptions: list = raw if isinstance(raw, list) else []

    # Filter low-confidence noise and ensure required keys exist
    clean = []
    for m in misconceptions:
        if not isinstance(m, dict):
            continue
        confidence = float(m.get("confidence", 0.0))
        if confidence < 0.4:
            continue
        clean.append(
            {
                "type": m.get("type", "unknown"),
                "description": m.get("description", ""),
                "confidence": confidence,
                "correction": m.get("correction", ""),
                "root_cause": m.get("root_cause", ""),
            }
        )

    # Persist each misconception for pattern analysis
    store = get_vector_store()
    for m in clean:
        store.add(
            text=f"Misconception ({m['type']}): {m['description']}",
            metadata={
                "topic": topic,
                "type": "misconception",
                "user_id": state["user_id"],
                "misconception_type": m["type"],
                "confidence": m["confidence"],
            },
        )

    return {"misconceptions": clean}


# ---------------------------------------------------------------------------
# Node 6 – feedback_node
# ---------------------------------------------------------------------------

def feedback_node(state: LearningState) -> Dict[str, Any]:
    """
    Generate targeted, encouraging feedback that directly addresses
    the evaluation result and each detected misconception.
    Updates the learner's profile.
    """
    topic: str = state["topic"]
    user_answer: str = state.get("user_answer", "")
    evaluation: dict = state.get("evaluation", {})
    misconceptions: list = state.get("misconceptions", [])
    question_text: str = _question_text(state)
    profile = get_profile(state["user_id"])

    user_prompt = build_feedback_prompt(
        evaluation, misconceptions, topic, user_answer, question_text, profile
    )
    feedback: dict = call_llm_json(FEEDBACK_SYSTEM_PROMPT, user_prompt)

    # Update learning profile now that we have all the signal
    updated_profile = update_profile(
        state["user_id"], topic, evaluation, misconceptions
    )

    chat_entry = {
        "role": "assistant",
        "type": "feedback",
        "content": feedback.get("message", ""),
        "metadata": feedback,
    }

    return {
        "learning_profile": updated_profile,
        "chat_history": [chat_entry],
    }


# ---------------------------------------------------------------------------
# Node 7 – router_node
# ---------------------------------------------------------------------------

def router_node(state: LearningState) -> Dict[str, Any]:
    """
    Decide the next learning action based on evaluation score and attempt count.

    Score > 0.8       → advance  (topic mastered, move on)
    Score 0.4 – 0.8   → followup (ask another question on same topic)
    Score < 0.4       → simplify (re-explain with simpler language)

    Attempt ceiling enforced to prevent infinite loops.
    """
    score: float = state["evaluation"].get("score", 0.0)
    attempts: int = state.get("attempts", 0) + 1  # increment here

    if attempts >= MAX_ATTEMPTS:
        # Force advance after ceiling to prevent infinite loop
        next_action = "advance"
    elif score > 0.8:
        next_action = "advance"
    elif score >= 0.4:
        next_action = "followup"
    else:
        next_action = "simplify"

    return {
        "next_action": next_action,
        "attempts": attempts,
    }
