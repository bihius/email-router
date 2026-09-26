from pydantic import BaseModel, EmailStr, Field

from app.departments import Department


class RouteRequest(BaseModel):
    email: EmailStr = Field(description="Sender address; used as Reply-To on the outbound mail.")
    message: str = Field(min_length=1, description="Free-form ticket text from the user.")


class RouteResponse(BaseModel):
    status: str
    department: Department
    to: str
