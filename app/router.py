from typing import Literal

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import Field, create_model

from app import mailer
from app.departments import DEPARTMENTS, Department, get_department
from app.llm import ollama_base_url, ollama_model, ollama_num_ctx, ollama_timeout
from app.text import text_for_model


class ModelDidNotCallTool(Exception):
    """The model answered with text instead of a send_email tool call."""


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


def invoke_agent(agent, send_email_tool, user_text: str) -> None:
    """Run one agent turn.

    The tool argument is the same function handed to the agent. This call does
    not use it. Tests call that function themselves, without a live model.
    """
    agent.invoke(
        {"messages": [{"role": "user", "content": user_text}]},
        config={"recursion_limit": 6},
    )


def route_ticket(*, message: str, reply_to: str) -> Department:
    """Ask a LangChain agent to call send_email, then return the department it chose.

    Reply-To and the original body are closed over by the tool. The model only
    picks a department name. Base64 is stripped from the text the model sees.
    """
    sent: list[Department] = []
    names = tuple(item.name for item in DEPARTMENTS)
    department_name = Literal.__getitem__(names)
    args_schema = create_model(
        "SendEmailArgs",
        department=(department_name, Field(description="Catalog department name.")),
    )

    @tool("send_email", args_schema=args_schema)
    def send_email(department: str) -> str:
        """Forward this ticket to exactly one department."""
        row = get_department(department)
        mailer.send_email(
            department=row,
            reply_to=reply_to,
            subject=f"Ticket for {row.name}",
            body=message,
        )
        sent.append(row)
        return f"sent to {row.email}"

    model = ChatOllama(
        model=ollama_model(),
        base_url=ollama_base_url(),
        num_ctx=ollama_num_ctx(),
        temperature=0,
        client_kwargs={"timeout": ollama_timeout()},
    )
    agent = create_agent(model, tools=[send_email], system_prompt=system_prompt())
    invoke_agent(agent, send_email, text_for_model(message))
    if not sent:
        raise ModelDidNotCallTool("model returned no send_email tool call")
    return sent[-1]
