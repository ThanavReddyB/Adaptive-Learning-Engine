import operator
from typing import Annotated, Any, Dict, List, TypedDict


class EvaluationResult(TypedDict):
    score: float
    label: str  # "correct" | "partial" | "incorrect"
    reasoning: str
    correct_elements: List[str]
    missing_elements: List[str]
    incorrect_elements: List[str]


class Misconception(TypedDict):
    type: str
    description: str
    confidence: float
    correction: str
    root_cause: str


class LearningProfile(TypedDict):
    weak_areas: List[str]
    strengths: List[str]
    progress: Dict[str, Any]


class LearningState(TypedDict):
    user_id: str
    topic: str
    chat_history: Annotated[List[Dict[str, Any]], operator.add]
    current_explanation: str
    current_question: str
    user_answer: str
    evaluation: EvaluationResult
    misconceptions: List[Misconception]
    learning_profile: LearningProfile
    retrieved_context: List[str]
    next_action: str
    attempts: int


def make_default_state(user_id: str, topic: str) -> LearningState:
    return LearningState(
        user_id=user_id,
        topic=topic,
        chat_history=[],
        current_explanation="",
        current_question="",
        user_answer="",
        evaluation={
            "score": 0.0,
            "label": "incorrect",
            "reasoning": "",
            "correct_elements": [],
            "missing_elements": [],
            "incorrect_elements": [],
        },
        misconceptions=[],
        learning_profile={
            "weak_areas": [],
            "strengths": [],
            "progress": {},
        },
        retrieved_context=[],
        next_action="",
        attempts=0,
    )
