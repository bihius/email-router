from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.departments import Department


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
                }
            ]
        }
    )

    status: Literal["sent"] = Field(
        description="sent means the tool call ran and MailHog accepted the message.",
        examples=["sent"],
    )
    department: Department = Field(
        description="Department the model selected.",
        examples=["it"],
    )
    to: str = Field(
        description="Inbox that received the ticket.",
        examples=["it@example.com"],
    )
