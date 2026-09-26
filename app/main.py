from fastapi import FastAPI

from app.departments import DEPARTMENT_EMAIL
from app.mailer import send_email
from app.schemas import RouteRequest, RouteResponse

app = FastAPI(
    title="E-mail Router",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
)


@app.post("/api/v1/route", response_model=RouteResponse)
def route_message(payload: RouteRequest) -> RouteResponse:
    """Accept a ticket and forward it by email. No LLM yet — department comes from the request."""
    send_email(
        department=payload.department,
        reply_to=str(payload.email),
        subject=f"Ticket for {payload.department.value}",
        body=payload.message,
    )
    return RouteResponse(
        status="sent",
        department=payload.department,
        to=DEPARTMENT_EMAIL[payload.department],
    )
