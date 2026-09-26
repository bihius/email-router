from typing import Literal

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app import mailer
from app.departments import DEPARTMENTS, Department, get_department
from app.llm import ollama_base_url, ollama_model, ollama_num_ctx, ollama_timeout
from app.text import text_for_model

DepartmentName = Literal[tuple(item.name for item in DEPARTMENTS)]


class SendEmailArgs(BaseModel):
    department: DepartmentName = Field(description="Catalog department name.")


class ModelDidNotCallTool(Exception):
    """The model answered with text instead of a send_email tool call."""


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


def route_ticket(*, message: str, reply_to: str) -> Department:
    """Ask a LangChain agent to call send_email, then return the department it chose.

    Reply-To and the original body are closed over by the tool, so the model
    only picks a department name. The model sees a cleaned copy of the message
    (see app.text); the mail carries the original.
    """
    sent: list[Department] = []

    # An unknown department name fails schema validation; the agent returns the
    # error to the model, which can retry within the recursion limit.
    @tool("send_email", args_schema=SendEmailArgs)
    def send_email(department: str) -> str:
        """Forward this ticket to exactly one department."""
        if sent:
            return f"already sent to {sent[0].email}"
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
    agent.invoke(
        {"messages": [{"role": "user", "content": text_for_model(message)}]},
        config={"recursion_limit": 6},
    )
    if not sent:
        raise ModelDidNotCallTool("model returned no send_email tool call")
    return sent[0]
