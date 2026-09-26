import unittest
from unittest.mock import patch

from app.departments import get_department
from app.router import ModelDidNotCallTool, route_ticket


class RouteTicketTest(unittest.TestCase):
    @patch("app.mailer.send_email")
    @patch("app.router.invoke_agent")
    def test_executes_send_email_from_tool_call(self, invoke_agent, send_email) -> None:
        def call_the_tool(agent, tool, user_text: str) -> None:
            del agent
            self.assertEqual(user_text, "Nie działa mi komputer")
            tool.invoke({"department": "it"})

        invoke_agent.side_effect = call_the_tool

        department = route_ticket(
            message="Nie działa mi komputer",
            reply_to="jan.nowak@example.com",
        )

        self.assertEqual(department, get_department("it"))
        send_email.assert_called_once()
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["reply_to"], "jan.nowak@example.com")
        self.assertEqual(kwargs["body"], "Nie działa mi komputer")
        self.assertEqual(kwargs["department"].name, "it")

    @patch("app.mailer.send_email")
    @patch("app.router.invoke_agent")
    def test_prose_answer_does_not_send(self, invoke_agent, send_email) -> None:
        with self.assertRaises(ModelDidNotCallTool):
            route_ticket(message="cześć", reply_to="a@example.com")
        send_email.assert_not_called()

    @patch("app.mailer.send_email")
    @patch("app.router.invoke_agent")
    def test_model_text_drops_base64_but_mail_keeps_it(self, invoke_agent, send_email) -> None:
        blob = "B" * 220
        original = f"Urlop na jutro\n{blob}"

        def call_the_tool(agent, tool, user_text: str) -> None:
            del agent
            self.assertNotIn(blob, user_text)
            self.assertIn("Urlop na jutro", user_text)
            tool.invoke({"department": "kadry"})

        invoke_agent.side_effect = call_the_tool
        route_ticket(message=original, reply_to="jan.nowak@example.com")
        self.assertIn(blob, send_email.call_args.kwargs["body"])


if __name__ == "__main__":
    unittest.main()
