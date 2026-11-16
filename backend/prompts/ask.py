from typing import Any, Dict

ASK_SYSTEM_PROMPT = """\
You are an expert educator designing conceptual assessment questions.
Your questions must test deep understanding, NOT memorisation or recall.

You MUST return a single, valid JSON object — no prose, no markdown fences.

REQUIRED SCHEMA:
{
  "question":          "<string – the question text, one or two sentences>",
  "question_type":     "<one of: conceptual | application | analysis | comparison>",
  "difficulty":        "<one of: beginner | intermediate | advanced>",
  "hint":              "<string – a subtle nudge that does NOT give away the answer>",
  "expected_concepts": ["<string>", ...],  // 2-5 concepts a good answer must demonstrate
  "avoid_keywords":    ["<string>", ...]   // terms the learner should NOT merely quote back
}

RULES:
• Questions MUST require the learner to explain, reason, or apply — not recite.
• Do NOT ask yes/no questions.
• Do NOT ask questions answerable by copy-pasting the explanation.
• Difficulty should escalate with attempt count.
• expected_concepts lists what an ideal answer must contain.
• avoid_keywords lists terms the question itself should not use verbatim.

EXAMPLE OUTPUT (topic = "hash maps", attempt = 1):
{
  "question": "A colleague claims a hash map always gives O(1) lookup time and is therefore always the best choice for fast retrieval. What would you tell them, and in what situations might a different data structure be preferable?",
  "question_type": "analysis",
  "difficulty": "intermediate",
  "hint": "Think about what happens when many keys end up in the same bucket.",
  "expected_concepts": ["worst-case O(n) due to collisions", "load factor", "when ordered access is needed", "memory overhead"],
  "avoid_keywords": ["hash map", "O(1)", "bucket"]
}\
"""


def build_ask_prompt(
    topic: str,
    explanation: Dict[str, Any],
    learning_profile: Dict[str, Any],
    attempts: int,
) -> str:
    if attempts == 0:
        difficulty = "beginner"
    elif attempts <= 2:
        difficulty = "intermediate"
    else:
        difficulty = "advanced"

    weak_areas = learning_profile.get("weak_areas", [])
    normal_explanation = explanation.get("normal", "")
    key_concepts = explanation.get("key_concepts", [])
    pitfalls = explanation.get("common_pitfalls", [])

    return f"""\
Topic: {topic}
Attempt number: {attempts}  (0-indexed, higher = harder question)
Target difficulty: {difficulty}

Explanation provided to the learner:
{normal_explanation}

Key concepts covered: {key_concepts}
Common pitfalls noted: {pitfalls}
Learner weak areas: {weak_areas or 'none identified yet'}

Design a question that:
1. Tests understanding of this specific topic at {difficulty} level.
2. Targets any listed weak areas if they are relevant.
3. Cannot be answered by repeating the explanation verbatim.
4. Requires reasoning, application, or analysis.

Return the JSON object only.\
"""
