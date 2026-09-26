from fastapi import FastAPI, HTTPException

from app.departments import DEPARTMENT_EMAIL
from app.router import ModelDidNotCallTool, route_ticket
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
    """Accept a ticket. Ollama picks the department by calling send_email."""
    try:
        department = route_ticket(message=payload.message, reply_to=str(payload.email))
    except ModelDidNotCallTool as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RouteResponse(
        status="sent",
        department=department,
        to=DEPARTMENT_EMAIL[department],
    )
