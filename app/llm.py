import os

import httpx


def ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")


def ollama_timeout() -> float:
    """Seconds to wait for one Ollama HTTP response. Set OLLAMA_TIMEOUT in .env."""
    return float(os.environ.get("OLLAMA_TIMEOUT", "180"))


def ask_ollama(prompt: str) -> str:
    """Send one plain chat message to Ollama and return the assistant text.

    No tools, no agent loop — just HTTP to /api/chat.
    """
    response = httpx.post(
        f"{ollama_base_url()}/api/chat",
        json={
            "model": ollama_model(),
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=ollama_timeout(),
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
