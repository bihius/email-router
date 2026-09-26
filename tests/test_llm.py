import unittest
from unittest.mock import MagicMock, patch

from app.llm import ask_ollama


class AskOllamaTest(unittest.TestCase):
    @patch("app.llm.httpx.post")
    def test_returns_assistant_content(self, post) -> None:
        post.return_value = MagicMock(
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={"message": {"role": "assistant", "content": "it"}}
            ),
        )

        answer = ask_ollama("Nie działa mi komputer")

        self.assertEqual(answer, "it")
        kwargs = post.call_args.kwargs
        self.assertFalse(kwargs["json"]["stream"])
        self.assertEqual(kwargs["json"]["messages"][0]["content"], "Nie działa mi komputer")


if __name__ == "__main__":
    unittest.main()
