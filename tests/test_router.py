import os
import unittest
from unittest.mock import patch

import httpx
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.config import ollama_think, router_engine
from app.departments import DEPARTMENTS, get_department
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
        department = route_ticket(message=message, reply_to="jan.nowak@example.com").department
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

    def test_model_that_keeps_calling_the_tool_still_succeeds(self) -> None:
        calls = [tool_call("other", f"call-{index}") for index in range(10)]
        department, _, send_email = run("Czy w piątek jest firmowa impreza?", *calls)

        self.assertEqual(department.name, "other")
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


def laya_answer(choice: str, probability: float):
    def post(url, *, json, timeout):
        answer = {"choice": choice, "probabilities": {choice: probability}, "confidence": 0.1}
        body = {"answers": {"department": answer}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    return post


class LayaRouteTest(unittest.TestCase):
    @patch("app.mailer.send_email")
    def test_laya_choice_is_mailed_with_reply_to_and_original_body(self, send_email) -> None:
        original = "Nie działa mi komputer\n-- \nJan Nowak"
        with patch("app.laya.httpx.post", side_effect=laya_answer("it", 0.91)) as post:
            routing = route_ticket(message=original, reply_to="jan.nowak@example.com", engine="laya")

        self.assertEqual((routing.engine, routing.department.name, routing.probability), ("laya", "it", 0.91))
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["department"].email, "it@example.com")
        self.assertEqual(kwargs["reply_to"], "jan.nowak@example.com")
        self.assertEqual(kwargs["body"], original)
        # Laya reads the cleaned text and may only answer with catalog names.
        request = post.call_args.kwargs["json"]
        self.assertEqual(request["state"], {"body": "Nie działa mi komputer"})
        options = request["questions"]["department"]["criteria"]
        self.assertEqual(set(options), {item.name for item in DEPARTMENTS})

    @patch("app.mailer.send_email")
    def test_laya_error_sends_nothing(self, send_email) -> None:
        def unavailable(url, *, json, timeout):
            return httpx.Response(503, request=httpx.Request("POST", url))

        with (
            patch("app.laya.httpx.post", side_effect=unavailable),
            self.assertRaises(httpx.HTTPStatusError),
        ):
            route_ticket(message="Nie działa mi komputer", reply_to="a@example.com", engine="laya")
        send_email.assert_not_called()


class EngineSwitchTest(unittest.TestCase):
    def test_defaults_to_ollama(self) -> None:
        with patch.dict(os.environ, clear=True):
            self.assertEqual(router_engine(), "ollama")

    def test_rejects_unknown_engine(self) -> None:
        with patch.dict(os.environ, {"ROUTER_ENGINE": "gpt"}), self.assertRaises(ValueError):
            router_engine()


class OllamaThinkTest(unittest.TestCase):
    def test_off_by_default_and_setting_reaches_the_model(self) -> None:
        cases = (({}, False), ({"OLLAMA_THINK": ""}, False), ({"OLLAMA_THINK": "false"}, False), ({"OLLAMA_THINK": "True"}, True))
        for env, expected in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                model = ScriptedModel(messages=iter([tool_call("it"), DONE]), seen=[])
                with (
                    patch("app.router.ChatOllama", return_value=model) as chat,
                    patch("app.mailer.send_email"),
                ):
                    route_ticket(message="Nie działa mi komputer", reply_to="jan.nowak@example.com")
                self.assertIs(chat.call_args.kwargs["reasoning"], expected)

    def test_rejects_invalid_value(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_THINK": "maybe"}), self.assertRaises(ValueError):
            ollama_think()


if __name__ == "__main__":
    unittest.main()
