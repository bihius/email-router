import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.departments import get_department
from app.main import app
from app.router import ModelDidNotCallTool, Routing


class RouteEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_docs_are_at_required_path(self) -> None:
        response = self.client.get("/api/v1/docs")
        self.assertEqual(response.status_code, 200)

    @patch("app.main.route_ticket", side_effect=ModelDidNotCallTool("no tool call"))
    def test_no_tool_call_is_a_502(self, route_ticket) -> None:
        response = self.client.post(
            "/api/v1/route",
            json={"email": "jan.nowak@example.com", "message": "cześć"},
        )

        self.assertEqual(response.status_code, 502)

    @patch(
        "app.main.route_ticket",
        return_value=Routing("laya", get_department("it"), 0.91),
    )
    def test_route_returns_engine_choice(self, route_ticket) -> None:
        response = self.client.post(
            "/api/v1/route",
            json={
                "email": "jan.nowak@example.com",
                "message": "Nie działa mi komputer",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "sent",
                "department": "it",
                "to": "it@example.com",
                "engine": "laya",
                "probability": 0.91,
            },
        )
        kwargs = route_ticket.call_args.kwargs
        self.assertEqual(kwargs["message"], "Nie działa mi komputer")
        self.assertEqual(kwargs["reply_to"], "jan.nowak@example.com")


if __name__ == "__main__":
    unittest.main()
