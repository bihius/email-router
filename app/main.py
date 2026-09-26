from fastapi import FastAPI, HTTPException

from app.config import router_engine
from app.router import ModelDidNotCallTool, route_ticket
from app.schemas import RouteRequest, RouteResponse

# Read once at import, so a typo in ROUTER_ENGINE stops the API at startup.
ENGINE = router_engine()

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
            "description": "Ollama engine only: the model never made a valid send_email call, so no mail was sent.",
            "content": {
                "application/json": {
                    "example": {"detail": "model returned no valid send_email tool call"}
                }
            },
        },
    },
)
def route_message(payload: RouteRequest) -> RouteResponse:
    """Accept a ticket and forward it to the department chosen by the configured engine.

    With `ROUTER_ENGINE=ollama` (default) an agent picks the department by calling
    send_email. With `ROUTER_ENGINE=laya` Laya answers a typed choice question.
    """
    try:
        routing = route_ticket(
            message=payload.message, reply_to=str(payload.email), engine=ENGINE
        )
    except ModelDidNotCallTool as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RouteResponse(
        status="sent",
        department=routing.department.name,
        to=routing.department.email,
        engine=routing.engine,
        probability=routing.probability,
    )
