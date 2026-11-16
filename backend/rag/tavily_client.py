from typing import Any, Dict, List

from tavily import TavilyClient

from utils.config import MIN_CONTEXT_CHARS, TAVILY_API_KEY

_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=TAVILY_API_KEY)
    return _client


def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Run a Tavily deep search and return a normalised list of result dicts.
    Each dict contains: source, content, url, score.
    Returns [] on any error so callers can degrade gracefully.
    """
    try:
        client = _get_client()
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
        )

        results: List[Dict[str, Any]] = []

        # Prepend the synthesised answer when available – highest value item
        if response.get("answer"):
            results.append(
                {
                    "source": "tavily_synthesised_answer",
                    "content": response["answer"],
                    "url": "",
                    "score": 1.0,
                }
            )

        for r in response.get("results", []):
            content = (r.get("content") or "").strip()
            if not content:
                continue
            results.append(
                {
                    "source": r.get("url", ""),
                    "content": content,
                    "url": r.get("url", ""),
                    "score": float(r.get("score", 0.0)),
                }
            )

        return results

    except Exception as exc:
        # Log and swallow – the caller will fall back to whatever context exists
        print(f"[TavilyClient] Search error for query '{query}': {exc}")
        return []


def is_context_sufficient(context: List[str]) -> bool:
    """Return True when the accumulated context text is long enough."""
    return sum(len(c) for c in context) >= MIN_CONTEXT_CHARS
