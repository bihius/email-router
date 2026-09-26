import os

import httpx


def ask_ollama(prompt: str) -> str:
    """Send one plain chat message to Ollama and return the assistant text.

    No tools, no agent loop — just HTTP to /api/chat.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
