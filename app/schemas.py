from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.config import Engine


class RouteRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "jan.nowak@example.com",
                    "message": "Nie działa mi komputer od rana i nie mogę się zalogować.",
                }
            ]
        }
    )

    email: EmailStr = Field(
        description="Sender address. Copied into the Reply-To header of the outbound mail.",
        examples=["jan.nowak@example.com"],
    )
    message: str = Field(
        min_length=1,
        description="Free-form ticket text. The model reads this and picks a department.",
        examples=["Nie działa mi komputer od rana i nie mogę się zalogować."],
    )


class RouteResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "sent",
                    "department": "it",
                    "to": "it@example.com",
                    "engine": "ollama",
                    "probability": None,
                }
            ]
        }
    )

    status: Literal["sent"] = Field(
        description="sent means a department was chosen and MailHog accepted the message.",
        examples=["sent"],
    )
    department: str = Field(
        description="Department name the model selected. Allowed names come from data/departments.csv.",
        examples=["it"],
    )
    to: str = Field(
        description="Inbox that received the ticket.",
        examples=["it@example.com"],
    )
    engine: Engine = Field(
        description="Model that chose the department, set by ROUTER_ENGINE.",
        examples=["ollama"],
    )
    probability: float | None = Field(
        description="Probability Laya gave the chosen department (uncalibrated). Null for Ollama, which reports none.",
        examples=[None, 0.93],
    )
