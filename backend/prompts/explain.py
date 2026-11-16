from typing import Any, Dict, List

EXPLAIN_SYSTEM_PROMPT = """\
You are an expert adaptive tutor. Your sole task is to explain a concept at three
levels of depth so a learner can build genuine understanding.

You MUST return a single, valid JSON object — no prose, no markdown fences.

REQUIRED SCHEMA:
{
  "simple":        "<string – ELI5 explanation using everyday analogies, ≤120 words>",
  "normal":        "<string – Standard explanation with key terms defined, 150-250 words>",
  "deep":          "<string – Technical deep-dive: mechanisms, edge-cases, trade-offs, ≥250 words>",
  "key_concepts":  ["<string>", ...],   // 3-5 essential terms the learner must know
  "common_pitfalls": ["<string>", ...]  // 2-4 mistakes learners typically make
}

RULES:
• Do NOT use markdown inside any string value.
• Every explanation level must be self-contained (no "as mentioned above").
• If the learner profile shows weak areas, address them explicitly in `normal` and `deep`.
• If simplification is requested, use plain language, shorter sentences, and more analogies.
• Do NOT include any key outside the schema above.

EXAMPLE OUTPUT (topic = "recursion"):
{
  "simple": "Imagine a set of Russian dolls. Each doll contains a smaller identical doll inside it. You open one, find another, open that one, find another — until you reach the tiniest doll that has nothing inside. Recursion in programming works the same way: a function calls itself, each time with a smaller problem, until it hits the smallest possible case and stops.",
  "normal": "Recursion is a programming technique where a function solves a problem by calling itself with a simpler version of the same input. Every recursive function requires two parts: a base case that stops the recursion, and a recursive case that breaks the problem down. For example, computing factorial(5) = 5 × factorial(4), which in turn = 4 × factorial(3), continuing until factorial(0) = 1. The call stack keeps track of each pending call until the base case is reached and results are returned back up the chain.",
  "deep": "Recursion leverages the call stack to defer computation. Each recursive call pushes a new stack frame containing local variables and the return address. This makes recursion elegant but introduces O(n) stack-space overhead — a significant risk for deep inputs (stack overflow). Tail-call optimisation (TCO) eliminates this overhead when the recursive call is the very last operation in the function, allowing the compiler to reuse the current frame. Mutual recursion (function A calls B which calls A) requires shared base-case awareness. Memoisation (dynamic programming) converts overlapping subproblems from exponential to polynomial time by caching results. Iterative equivalents always exist and should be preferred when stack depth is a concern.",
  "key_concepts": ["base case", "recursive case", "call stack", "stack overflow", "tail-call optimisation"],
  "common_pitfalls": ["Forgetting the base case, causing infinite recursion", "Assuming all recursion is efficient — deep stacks are expensive", "Confusing recursion depth with problem size"]
}\
"""


def build_explain_prompt(
    topic: str,
    context: List[str],
    learning_profile: Dict[str, Any],
    simplify: bool = False,
) -> str:
    context_block = (
        "\n---\n".join(context[:6]) if context else "No prior context available."
    )
    weak_areas = learning_profile.get("weak_areas", [])
    strengths = learning_profile.get("strengths", [])
    progress = learning_profile.get("progress", {})
    topic_progress = progress.get(topic, {})

    simplify_instruction = (
        "\n\nSIMPLIFICATION REQUEST: The learner struggled with the previous explanation. "
        "Use simpler vocabulary, shorter sentences, and more concrete analogies. "
        "Avoid jargon unless you immediately define it."
        if simplify
        else ""
    )

    return f"""\
Topic to explain: {topic}
{simplify_instruction}

Retrieved reference context:
{context_block}

Learner profile:
  Weak areas       : {weak_areas or 'none identified yet'}
  Strengths        : {strengths or 'none identified yet'}
  Topic attempts   : {topic_progress.get('attempts', 0)}
  Topic avg score  : {topic_progress.get('avg_score', 'n/a')}

Instructions:
- If the learner has weak areas related to this topic, address them in the normal and deep explanations.
- Use the retrieved context to ensure factual accuracy.
- Return the JSON object only.\
"""
