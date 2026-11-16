from typing import Any, Dict, List, Optional

from models.state import LearningProfile

# In-memory store keyed by user_id
_profiles: Dict[str, LearningProfile] = {}


def get_profile(user_id: str) -> LearningProfile:
    if user_id not in _profiles:
        _profiles[user_id] = LearningProfile(
            weak_areas=[],
            strengths=[],
            progress={},
        )
    return _profiles[user_id]


def update_profile(
    user_id: str,
    topic: str,
    evaluation: Dict[str, Any],
    misconceptions: List[Dict[str, Any]],
) -> LearningProfile:
    profile = get_profile(user_id)
    score: float = float(evaluation.get("score", 0.0))

    # ── Per-topic progress ──────────────────────────────────────────────
    if topic not in profile["progress"]:
        profile["progress"][topic] = {
            "attempts": 0,
            "scores": [],
            "avg_score": 0.0,
            "last_label": "incorrect",
        }

    tp = profile["progress"][topic]
    tp["attempts"] += 1
    tp["scores"].append(score)
    tp["avg_score"] = round(sum(tp["scores"]) / len(tp["scores"]), 4)
    tp["last_label"] = evaluation.get("label", "incorrect")

    # ── Strengths / weak-areas by topic ─────────────────────────────────
    if score >= 0.8:
        if topic not in profile["strengths"]:
            profile["strengths"].append(topic)
        if topic in profile["weak_areas"]:
            profile["weak_areas"].remove(topic)
    elif score < 0.4:
        if topic not in profile["weak_areas"]:
            profile["weak_areas"].append(topic)
        if topic in profile["strengths"]:
            profile["strengths"].remove(topic)

    # ── Fine-grained misconception tracking ─────────────────────────────
    for m in misconceptions:
        m_type: str = m.get("type", "")
        confidence: float = float(m.get("confidence", 0.0))
        if m_type and confidence >= 0.6:
            tag = f"{topic}::{m_type}"
            if tag not in profile["weak_areas"]:
                profile["weak_areas"].append(tag)

    _profiles[user_id] = profile
    return profile


def reset_profile(user_id: str) -> None:
    """Hard reset – used for testing or explicit user request."""
    _profiles[user_id] = LearningProfile(
        weak_areas=[],
        strengths=[],
        progress={},
    )


def all_profiles() -> Dict[str, LearningProfile]:
    return dict(_profiles)
