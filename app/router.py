from dataclasses import dataclass
from typing import Literal

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field

from app import laya, mailer
from app.config import Engine, ollama_base_url, ollama_model, ollama_num_ctx, ollama_think, ollama_timeout
from app.departments import DEPARTMENTS, Department, get_department
from app.text import text_for_model

DepartmentName = Literal[tuple(item.name for item in DEPARTMENTS)]


class SendEmailArgs(BaseModel):
    department: DepartmentName = Field(description="Catalog department name.")


class ModelDidNotCallTool(Exception):
    """The model answered with text instead of a send_email tool call."""


@dataclass(frozen=True)
class Routing:
    engine: Engine
    department: Department
    probability: float | None = None


def system_prompt() -> str:
    """Fixed routing rule, plus one line per row in the catalog."""
    lines = [
        "You route one internal ticket by calling send_email exactly once.",
        "Do not answer with prose.",
        "",
        "Departments:",
    ]
    lines.extend(f"- {item.name}: {item.description}" for item in DEPARTMENTS)
    lines.append("")
    lines.append("If two descriptions match, prefer the narrower one.")
    return "\n".join(lines)


def forward(department: Department, *, message: str, reply_to: str) -> None:
    """Mail the original ticket to the department, with Reply-To set to the sender."""
    mailer.send_email(
        department=department,
        reply_to=reply_to,
        subject=f"Ticket for {department.name}",
        body=message,
    )


def route_ticket(*, message: str, reply_to: str, engine: Engine = "ollama") -> Routing:
    """Pick a department with the configured engine and forward the ticket there.

    Both engines see a cleaned copy of the message (see app.text); the mail carries
    the original.
    """
    text = text_for_model(message)
    if engine == "laya":
        department, probability = laya.choose_department(text)
        forward(department, message=message, reply_to=reply_to)
        return Routing(engine, department, probability)
    return Routing(engine, _route_with_agent(text, message=message, reply_to=reply_to))


def _route_with_agent(text: str, *, message: str, reply_to: str) -> Department:
    """Ask a LangChain agent to call send_email, then return the department it chose.

    Reply-To and the original body are closed over by the tool, so the model
    only picks a department name.
    """
    sent: list[Department] = []

    # An unknown department name fails schema validation; the agent returns the
    # error to the model, which can retry within the recursion limit.
    @tool("send_email", args_schema=SendEmailArgs)
    def send_email(department: str) -> str:
        """Forward this ticket to exactly one department."""
        if sent:
            return f"Already forwarded to {sent[0].name}. Do not call send_email again."
        row = get_department(department)
        forward(row, message=message, reply_to=reply_to)
        sent.append(row)
        return f"Forwarded to {row.name}. The ticket is handled; do not call any tool again."

    model = ChatOllama(
        model=ollama_model(),
        base_url=ollama_base_url(),
        num_ctx=ollama_num_ctx(),
        temperature=0,
        reasoning=ollama_think(),
        client_kwargs={"timeout": ollama_timeout()},
    )
    agent = create_agent(model, tools=[send_email], system_prompt=system_prompt())
    try:
        agent.invoke(
            {"messages": [{"role": "user", "content": text}]},
            config={"recursion_limit": 6},
        )
    except GraphRecursionError:
        # A model can keep calling the tool after the mail went out; the guard above
        # stops duplicates, and the ticket is still delivered. Without a mail the
        # model only produced invalid calls, which is the same failure as prose.
        pass
    if not sent:
        raise ModelDidNotCallTool("model returned no valid send_email tool call")
    return sent[0]
