import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.departments import get_department
from app.main import app
from app.router import ModelDidNotCallTool


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

    @patch("app.main.route_ticket", return_value=get_department("it"))
    def test_route_uses_model_choice(self, route_ticket) -> None:
        response = self.client.post(
            "/api/v1/route",
            json={
                "email": "jan.nowak@example.com",
                "message": "Nie działa mi komputer",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["department"], "it")
        self.assertEqual(response.json()["to"], "it@example.com")
        route_ticket.assert_called_once_with(
            message="Nie działa mi komputer",
            reply_to="jan.nowak@example.com",
        )


if __name__ == "__main__":
    unittest.main()
