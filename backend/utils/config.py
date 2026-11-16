import os

from dotenv import load_dotenv

load_dotenv()

OR_KEY: str = os.getenv("OR_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "meta-llama/llama-3.3-70b-instruct")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
VECTOR_DIM: int = 384  # all-MiniLM-L6-v2 output dimension

# Safety limits
MAX_ATTEMPTS: int = int(os.getenv("MAX_ATTEMPTS", "5"))
LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "90"))
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
MIN_CONTEXT_CHARS: int = int(os.getenv("MIN_CONTEXT_CHARS", "300"))


def validate_config() -> None:
    missing = []
    if not OR_KEY:
        missing.append("OR_KEY")
    if not TAVILY_API_KEY:
        missing.append("TAVILY_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Please set them in your .env file."
        )
