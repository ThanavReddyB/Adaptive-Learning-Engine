from typing import Any, Dict, List

EVALUATE_SYSTEM_PROMPT = """\
You are an expert educator evaluating a student's conceptual answer.

You MUST return a single, valid JSON object — no prose, no markdown fences.

REQUIRED SCHEMA:
{
  "score":              <float between 0.0 and 1.0>,
  "label":              "<one of: correct | partial | incorrect>",
  "reasoning":          "<string – 2-4 sentences explaining the score>",
  "correct_elements":   ["<string>", ...],  // what the student correctly demonstrated
  "missing_elements":   ["<string>", ...],  // key concepts absent from the answer
  "incorrect_elements": ["<string>", ...]   // explicit conceptual errors made
}

SCORING RUBRIC:
  0.80 – 1.00 → label = "correct"    (core concepts clearly demonstrated, minor gaps acceptable)
  0.40 – 0.79 → label = "partial"    (some correct ideas but missing key concepts or has errors)
  0.00 – 0.39 → label = "incorrect"  (wrong or missing understanding of core concepts)

RULES:
• Do NOT penalise for minor spelling, grammar, or informal phrasing.
• DO penalise for conceptual errors and dangerous oversimplifications.
• Evaluate against `expected_concepts`, not the explanation wording.
• Be objective: support every score with explicit evidence from the student answer.
• correct_elements / missing_elements / incorrect_elements may be empty arrays [].

EXAMPLE OUTPUT:
{
  "score": 0.65,
  "label": "partial",
  "reasoning": "The student correctly identifies hash maps as key-value stores and mentions average-case O(1) lookup. However, they explicitly state O(1) is guaranteed in all cases, which is incorrect, and they do not mention collision resolution or worst-case behaviour.",
  "correct_elements": ["key-value pairs", "average O(1) lookup", "fast access for large datasets"],
  "missing_elements": ["collision handling", "worst-case O(n)", "load factor impact"],
  "incorrect_elements": ["claimed O(1) is always guaranteed regardless of collisions"]
}\
"""


def build_evaluate_prompt(
    question: str,
    user_answer: str,
    expected_concepts: List[str],
    topic: str,
    explanation_given: str,
) -> str:
    concepts_block = (
        "\n".join(f"  - {c}" for c in expected_concepts)
        if expected_concepts
        else "  (no explicit list provided)"
    )

    return f"""\
Topic: {topic}

Explanation that was given to the learner:
{explanation_given}

Question posed to the learner:
{question}

Concepts a good answer should demonstrate:
{concepts_block}

Learner's answer:
{user_answer}

Evaluate the answer strictly according to the rubric.
Return the JSON object only.\
"""
