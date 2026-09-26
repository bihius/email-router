import json
import os
from typing import Any

import httpx

from app.departments import Department
from app.mailer import send_email

SYSTEM_PROMPT = """You route one internal ticket by calling send_email exactly once.
Do not answer with prose.

department:
- kadry: employment admin for one person (leave, sick leave, contract, pay, working time). Example: vacation tomorrow.
- human_resources: people processes that are not that admin (hiring, onboarding, review, conflict, development).
- it: something is broken or access is missing. Example: computer does not work, cannot log in.
- help_desk: a service request with no outage (how-to, equipment request, procedure question).
- other: none of the above.

If two match, prefer the narrower one: an outage beats help_desk; employment admin beats human_resources.
"""


class ModelDidNotCallTool(Exception):
    """The model answered with text instead of a send_email tool call."""


def send_email_tool() -> dict[str, Any]:
    """JSON schema Ollama receives. The model may only pick a department."""
    return {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Forward the ticket to one department.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "enum": [item.value for item in Department],
                    }
                },
                "required": ["department"],
            },
        },
    }


def route_ticket(*, message: str, reply_to: str) -> Department:
    """Ask Ollama to call send_email, then run that call in Python.

    Reply-To is not a model argument. It always comes from the HTTP request.
    """
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "stream": False,
            "tools": [send_email_tool()],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        },
        timeout=180.0,
    )
    response.raise_for_status()
    department = _department_from_tool_call(response.json())
    send_email(
        department=department,
        reply_to=reply_to,
        subject=f"Ticket for {department.value}",
        body=message,
    )
    return department


def _department_from_tool_call(payload: dict[str, Any]) -> Department:
    message = payload.get("message") or {}
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        if function.get("name") != "send_email":
            continue
        arguments = function.get("arguments") or {}
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        raw = arguments.get("department", Department.OTHER.value)
        try:
            return Department(raw)
        except ValueError:
            return Department.OTHER
    raise ModelDidNotCallTool("model returned no send_email tool call")
