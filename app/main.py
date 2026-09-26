from fastapi import FastAPI, HTTPException

from app.router import ModelDidNotCallTool, route_ticket
from app.schemas import RouteRequest, RouteResponse

app = FastAPI(
    title="E-mail Router",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url=None,
)


@app.post(
    "/api/v1/route",
    response_model=RouteResponse,
    responses={
        422: {
            "description": "The JSON body is invalid. For example the email is not an address, or message is empty.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "email"],
                                "msg": "value is not a valid email address",
                                "input": "nie-adres",
                            }
                        ]
                    }
                }
            },
        },
        502: {
            "description": "Ollama answered with text and did not call send_email, so no mail was sent.",
            "content": {
                "application/json": {
                    "example": {"detail": "model returned no send_email tool call"}
                }
            },
        },
    },
)
def route_message(payload: RouteRequest) -> RouteResponse:
    """Accept a ticket. Ollama picks the department by calling send_email."""
    try:
        department = route_ticket(message=payload.message, reply_to=str(payload.email))
    except ModelDidNotCallTool as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RouteResponse(
        status="sent",
        department=department.name,
        to=department.email,
    )
