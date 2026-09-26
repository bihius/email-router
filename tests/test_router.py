import unittest
from unittest.mock import MagicMock, patch

from app.departments import Department
from app.router import ModelDidNotCallTool, route_ticket


def _ollama_response(body: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=body)
    return response


class RouteTicketTest(unittest.TestCase):
    @patch("app.router.send_email")
    @patch("app.router.httpx.post")
    def test_executes_send_email_from_tool_call(self, post, send_email) -> None:
        post.return_value = _ollama_response(
            {
                "message": {
                    "tool_calls": [
                        {
                            "function": {
                                "name": "send_email",
                                "arguments": {"department": "it"},
                            }
                        }
                    ]
                }
            }
        )

        department = route_ticket(
            message="Nie działa mi komputer",
            reply_to="jan.nowak@example.com",
        )

        self.assertEqual(department, Department.IT)
        send_email.assert_called_once()
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["reply_to"], "jan.nowak@example.com")
        self.assertEqual(kwargs["body"], "Nie działa mi komputer")
        self.assertEqual(kwargs["department"], Department.IT)
        tools = post.call_args.kwargs["json"]["tools"]
        self.assertEqual(tools[0]["function"]["name"], "send_email")

    @patch("app.router.send_email")
    @patch("app.router.httpx.post")
    def test_prose_answer_does_not_send(self, post, send_email) -> None:
        post.return_value = _ollama_response(
            {"message": {"content": "it", "tool_calls": []}}
        )

        with self.assertRaises(ModelDidNotCallTool):
            route_ticket(message="cześć", reply_to="a@example.com")
        send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
