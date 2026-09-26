import json
from typing import Any

import httpx

from app.departments import DEPARTMENTS, Department, get_department
from app.llm import ollama_base_url, ollama_model, ollama_num_ctx, ollama_timeout
from app.mailer import send_email

def system_prompt() -> str:
    """Fixed routing rule, plus one line per row in the catalog."""
    lines = [
        "You route one internal ticket by calling send_email exactly once.",
        "Do not answer with prose.",
        "",
        "department:",
    ]
    lines.extend(f"- {item.name}: {item.description}" for item in DEPARTMENTS)
    lines.append("")
    lines.append("If two descriptions match, prefer the narrower one.")
    return "\n".join(lines)


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
                        "enum": [item.name for item in DEPARTMENTS],
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
    response = httpx.post(
        f"{ollama_base_url()}/api/chat",
        json={
            "model": ollama_model(),
            "stream": False,
            "tools": [send_email_tool()],
            "options": {"num_ctx": ollama_num_ctx()},
            "messages": [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": message},
            ],
        },
        timeout=ollama_timeout(),
    )
    response.raise_for_status()
    department = _department_from_tool_call(response.json())
    send_email(
        department=department,
        reply_to=reply_to,
        subject=f"Ticket for {department.name}",
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
        raw = arguments.get("department", "other")
        return get_department(str(raw))
    raise ModelDidNotCallTool("model returned no send_email tool call")
