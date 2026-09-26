import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class RouteEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_docs_are_at_required_path(self) -> None:
        response = self.client.get("/api/v1/docs")
        self.assertEqual(response.status_code, 200)

    @patch("app.main.send_email")
    def test_route_sends_mail_with_reply_to(self, send_email) -> None:
        response = self.client.post(
            "/api/v1/route",
            json={
                "email": "jan.nowak@example.com",
                "message": "Nie działa mi komputer",
                "department": "it",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "sent",
                "department": "it",
                "to": "it@example.com",
            },
        )
        send_email.assert_called_once()
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["reply_to"], "jan.nowak@example.com")
        self.assertEqual(kwargs["body"], "Nie działa mi komputer")
        self.assertEqual(kwargs["department"].value, "it")


if __name__ == "__main__":
    unittest.main()
