from typing import Any, Dict, List

FEEDBACK_SYSTEM_PROMPT = """\
You are an expert adaptive tutor delivering targeted, evidence-based feedback.

You MUST return a single, valid JSON object — no prose, no markdown fences.

REQUIRED SCHEMA:
{
  "message":             "<string – 2-4 sentence personalised summary of performance>",
  "corrections":         ["<string>", ...],   // one entry per misconception: state the error then the fix
  "reinforcements":      ["<string>", ...],   // explicit praise for each correct element
  "next_focus":          "<string – the single most important concept to study next>",
  "encouragement":       "<string – motivational message calibrated to score: honest, not patronising>",
  "resources_suggested": ["<string>", ...]    // 2-4 specific subtopics or concepts to review
}

TONE RULES:
  score ≥ 0.8  → celebratory but forward-looking; point to next challenge
  score 0.4-0.8 → balanced; highlight wins first, then correct errors precisely
  score < 0.4  → empathetic; normalise struggle, provide clear corrective path

CONTENT RULES:
• corrections must quote or closely paraphrase what the student said before giving the fix.
• reinforcements must reference specific correct things the student said.
• Do NOT give vague praise ("good job!") without citing what was good.
• Do NOT repeat the same correction twice across corrections[].
• resources_suggested should be subtopics, not generic advice like "study more".

EXAMPLE OUTPUT (score = 0.65, topic = "hash maps"):
{
  "message": "You have a solid foundation — you correctly described the key-value structure and the hashing process. The main gap is around what happens when two keys produce the same hash, which also affects your time-complexity claim.",
  "corrections": [
    "You stated hash maps 'always give O(1) lookup'. In reality O(1) is the average case; if many keys collide in the same bucket, lookup degrades to O(n). The actual guarantee depends on load factor and collision resolution strategy.",
    "Your description implied all hash functions distribute keys perfectly. Real hash functions can cluster keys, which is why a good implementation monitors load factor and rehashes when it gets too high."
  ],
  "reinforcements": [
    "Correct: you accurately described key-value pairs as the fundamental data model.",
    "Correct: you mentioned that hashing converts a key into an index — that is precisely right."
  ],
  "next_focus": "Collision resolution strategies (chaining vs open addressing) and how load factor triggers rehashing",
  "encouragement": "You are 65% of the way there. One focused session on collision handling will push you into confident territory.",
  "resources_suggested": ["Hash collision and chaining", "Open addressing and linear probing", "Load factor and rehashing", "Worst-case vs average-case complexity"]
}\
"""


def build_feedback_prompt(
    evaluation: Dict[str, Any],
    misconceptions: List[Dict[str, Any]],
    topic: str,
    user_answer: str,
    question: str,
    learning_profile: Dict[str, Any],
) -> str:
    score = evaluation.get("score", 0.0)
    label = evaluation.get("label", "unknown")
    correct_els = evaluation.get("correct_elements", [])
    missing_els = evaluation.get("missing_elements", [])
    incorrect_els = evaluation.get("incorrect_elements", [])
    reasoning = evaluation.get("reasoning", "")
    weak_areas = learning_profile.get("weak_areas", [])
    strengths = learning_profile.get("strengths", [])
    progress = learning_profile.get("progress", {})
    topic_progress = progress.get(topic, {})

    misconception_block = (
        "\n".join(
            f"  [{i+1}] type={m.get('type')} confidence={m.get('confidence')}: {m.get('description')}"
            for i, m in enumerate(misconceptions)
        )
        if misconceptions
        else "  None detected."
    )

    return f"""\
Topic: {topic}

Question: {question}

Student's answer: {user_answer}

Evaluation:
  Score             : {score}  ({label})
  Evaluator reasoning: {reasoning}
  Correct elements  : {correct_els or 'none'}
  Missing elements  : {missing_els or 'none'}
  Incorrect elements: {incorrect_els or 'none'}

Detected misconceptions:
{misconception_block}

Learner profile:
  Weak areas       : {weak_areas or 'none identified yet'}
  Strengths        : {strengths or 'none identified yet'}
  Topic attempts   : {topic_progress.get('attempts', 0)}
  Topic avg score  : {topic_progress.get('avg_score', 'n/a')}

Generate targeted, constructive feedback following the tone and content rules.
Return the JSON object only.\
"""
