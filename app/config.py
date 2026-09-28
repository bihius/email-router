import os
from typing import Literal

Engine = Literal["ollama", "laya"]
ENGINES: tuple[Engine, ...] = ("ollama", "laya")


def router_engine() -> Engine:
    """Which model routes tickets: the Ollama tool-calling agent (default) or Laya."""
    value = os.environ.get("ROUTER_ENGINE", "ollama").strip().lower()
    if value not in ENGINES:
        raise ValueError(f"ROUTER_ENGINE must be one of {', '.join(ENGINES)}, got {value!r}")
    return value


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen3:8b")


def ollama_timeout() -> float:
    """Seconds to wait for one Ollama HTTP response."""
    return float(os.environ.get("OLLAMA_TIMEOUT", "300"))


def ollama_num_ctx() -> int:
    """Context tokens allocated when the model loads."""
    return int(os.environ.get("OLLAMA_NUM_CTX", "2048"))


def laya_url() -> str:
    return os.environ.get("LAYA_URL", "http://laya:8000").rstrip("/")
