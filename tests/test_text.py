import unittest

from app.text import text_for_model


class TextForModelTest(unittest.TestCase):
    def test_drops_a_base64_footer_and_keeps_the_words(self) -> None:
        blob = "A" * 240
        message = f"Nie działa mi komputer.\n\n{blob}\nPozdrawiam"
        cleaned = text_for_model(message)
        self.assertIn("Nie działa mi komputer", cleaned)
        self.assertIn("[attachment omitted]", cleaned)
        self.assertNotIn(blob, cleaned)

    def test_drops_a_data_uri(self) -> None:
        message = "Urlop na jutro data:image/png;base64," + ("A" * 40)
        cleaned = text_for_model(message)
        self.assertIn("Urlop na jutro", cleaned)
        self.assertNotIn("data:image", cleaned)


if __name__ == "__main__":
    unittest.main()
