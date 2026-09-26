import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.departments import Department
from app.main import app


class RouteEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_docs_are_at_required_path(self) -> None:
        response = self.client.get("/api/v1/docs")
        self.assertEqual(response.status_code, 200)

    def test_openapi_shows_a_real_ticket(self) -> None:
        schema = self.client.get("/api/v1/openapi.json").json()
        request_schema = schema["components"]["schemas"]["RouteRequest"]
        example = request_schema["examples"][0]
        self.assertIn("komputer", example["message"])
        self.assertEqual(example["email"], "jan.nowak@example.com")
        response_schema = schema["components"]["schemas"]["RouteResponse"]
        self.assertEqual(response_schema["examples"][0]["status"], "sent")
        self.assertIn("Department", schema["components"]["schemas"])
        self.assertNotIn("HTTPValidationError", schema["components"]["schemas"])
        invalid = schema["paths"]["/api/v1/route"]["post"]["responses"]["422"]
        self.assertEqual(
            invalid["content"]["application/json"]["example"]["detail"][0]["loc"],
            ["body", "email"],
        )

    @patch("app.main.route_ticket", return_value=Department.IT)
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
