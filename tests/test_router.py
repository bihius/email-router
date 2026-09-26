import unittest
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.departments import get_department
from app.router import ModelDidNotCallTool, route_ticket


class ScriptedModel(GenericFakeChatModel):
    """Replays fixed AI messages and records what the agent sent to the model."""

    seen: list = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(messages)
        return super()._generate(messages, *args, **kwargs)


def tool_call(department: str, call_id: str = "call-1") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": "send_email", "args": {"department": department}, "id": call_id}],
    )


DONE = AIMessage(content="Sent.")


def run(message: str, *replies: AIMessage):
    """Route one ticket against a scripted model. Returns (result, model, send_email mock)."""
    model = ScriptedModel(messages=iter([*replies, DONE]), seen=[])
    with (
        patch("app.router.ChatOllama", return_value=model),
        patch("app.mailer.send_email") as send_email,
    ):
        department = route_ticket(message=message, reply_to="jan.nowak@example.com")
    return department, model, send_email


class RouteTicketTest(unittest.TestCase):
    def test_tool_call_sends_mail_with_reply_to_and_original_body(self) -> None:
        department, _, send_email = run("Nie działa mi komputer", tool_call("it"))

        self.assertEqual(department, get_department("it"))
        send_email.assert_called_once()
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["department"].email, "it@example.com")
        self.assertEqual(kwargs["reply_to"], "jan.nowak@example.com")
        self.assertEqual(kwargs["body"], "Nie działa mi komputer")

    def test_repeated_tool_call_sends_only_one_mail(self) -> None:
        _, _, send_email = run("Nie działa mi komputer", tool_call("it", "a"), tool_call("it", "b"))

        send_email.assert_called_once()

    def test_prose_answer_does_not_send(self) -> None:
        with self.assertRaises(ModelDidNotCallTool):
            run("cześć", AIMessage(content="Hello, how can I help?"))

    def test_unknown_department_is_rejected_and_model_can_retry(self) -> None:
        department, _, send_email = run(
            "Chciałbym zgłosić urlop na jutro",
            tool_call("payroll", "call-1"),
            tool_call("kadry", "call-2"),
        )

        self.assertEqual(department.name, "kadry")
        send_email.assert_called_once()

    def test_parallel_tool_calls_send_only_one_mail(self) -> None:
        double = AIMessage(
            content="",
            tool_calls=[
                {"name": "send_email", "args": {"department": "it"}, "id": "a"},
                {"name": "send_email", "args": {"department": "help_desk"}, "id": "b"},
            ],
        )
        _, _, send_email = run("Nie działa mi komputer", double)

        send_email.assert_called_once()

    def test_model_sees_cleaned_text_but_mail_keeps_original(self) -> None:
        blob = "B" * 220
        original = f"Urlop na jutro\n{blob}\n-- \nJan Nowak"
        _, model, send_email = run(original, tool_call("kadry"))

        user_text = model.seen[0][-1].content
        self.assertIn("Urlop na jutro", user_text)
        self.assertNotIn(blob, user_text)
        self.assertNotIn("Jan Nowak", user_text)
        self.assertEqual(send_email.call_args.kwargs["body"], original)


if __name__ == "__main__":
    unittest.main()
