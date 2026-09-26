import os


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


def ollama_timeout() -> float:
    """Seconds to wait for one Ollama HTTP response."""
    return float(os.environ.get("OLLAMA_TIMEOUT", "180"))


def ollama_num_ctx() -> int:
    """Context tokens allocated when the model loads."""
    return int(os.environ.get("OLLAMA_NUM_CTX", "2048"))
