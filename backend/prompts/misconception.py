from typing import Any, Dict

MISCONCEPTION_SYSTEM_PROMPT = """\
You are an expert in learning science specialising in misconception analysis.

You MUST return a valid JSON array — no prose, no markdown fences.
Return an empty array [] if no misconceptions are detected.

EACH ITEM IN THE ARRAY MUST MATCH THIS SCHEMA:
{
  "type":        "<one of the categories listed below>",
  "description": "<string – precise description referencing what the student actually said>",
  "confidence":  <float between 0.0 and 1.0>,
  "correction":  "<string – the accurate understanding that replaces this misconception>",
  "root_cause":  "<string – likely reason this misconception formed>"
}

MISCONCEPTION CATEGORIES:
  overgeneralization  – applying a rule beyond its valid scope
  oversimplification  – ignoring important nuance, conditions, or edge cases
  false_analogy       – using an incorrect or misleading mental model
  causal_confusion    – reversing or conflating cause and effect
  incomplete_model    – missing a critical component of the concept
  terminology_confusion – misusing or conflating technical terms

RULES:
• Only report misconceptions with confidence ≥ 0.4.
• Quote or closely paraphrase what the student said when describing the misconception.
• Do NOT report omissions as misconceptions — only report things the student said that were wrong.
• confidence = 1.0 is reserved for unambiguous, explicit errors.

EXAMPLE OUTPUT:
[
  {
    "type": "overgeneralization",
    "description": "Student stated 'hash maps are always O(1)' without any qualification",
    "confidence": 0.92,
    "correction": "Hash maps achieve O(1) average-case lookup, but degrade to O(n) in the worst case when many keys collide in the same bucket.",
    "root_cause": "Learner likely encountered O(1) described as the typical case and assumed it was universal."
  },
  {
    "type": "incomplete_model",
    "description": "Student described hashing but never mentioned what happens when two keys produce the same hash",
    "confidence": 0.75,
    "correction": "Every hash map implementation must have a collision resolution strategy (e.g., chaining or open addressing).",
    "root_cause": "Introductory materials often gloss over collision handling."
  }
]\
"""


def build_misconception_prompt(
    user_answer: str,
    evaluation: Dict[str, Any],
    topic: str,
    question: str,
) -> str:
    incorrect = evaluation.get("incorrect_elements", [])
    missing = evaluation.get("missing_elements", [])
    score = evaluation.get("score", 0.0)
    label = evaluation.get("label", "unknown")
    reasoning = evaluation.get("reasoning", "")

    return f"""\
Topic: {topic}

Question the student was answering:
{question}

Student's answer:
{user_answer}

Evaluation summary:
  Score   : {score}  ({label})
  Reasoning: {reasoning}
  Incorrect elements flagged: {incorrect or 'none'}
  Missing elements flagged  : {missing or 'none'}

Analyse the student's answer for genuine misconceptions — things they said that were
conceptually wrong, not merely things they omitted.
Return the JSON array only.\
"""
