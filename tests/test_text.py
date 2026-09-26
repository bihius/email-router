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

    def test_drops_rfc_signature_footer(self) -> None:
        message = "The computer does not start.\n\n-- \nJan Nowak\njan@example.com"
        cleaned = text_for_model(message)
        self.assertEqual(cleaned, "The computer does not start.")
        self.assertNotIn("Jan Nowak", cleaned)

    def test_drops_two_hyphen_footer(self) -> None:
        message = "Leave for tomorrow.\n--\nRegards"
        cleaned = text_for_model(message)
        self.assertEqual(cleaned, "Leave for tomorrow.")
        self.assertNotIn("Regards", cleaned)

    def test_delimiter_allows_trailing_spaces_and_tabs(self) -> None:
        message = "Leave for tomorrow.\n-- \t  \nRegards"
        self.assertEqual(text_for_model(message), "Leave for tomorrow.")

    def test_keeps_double_hyphen_inside_a_sentence(self) -> None:
        message = "The range is 1--10 and the flag is --verbose."
        self.assertEqual(text_for_model(message), message)

    def test_does_not_cut_on_three_hyphens(self) -> None:
        message = "Start of the ticket.\n---\nThis line stays."
        self.assertEqual(text_for_model(message), message)

    def test_does_not_cut_a_line_with_other_words(self) -> None:
        message = "Start of the ticket.\n-- not a delimiter\nThis line stays."
        self.assertEqual(text_for_model(message), message)

    def test_strips_blob_then_cuts_footer(self) -> None:
        blob = "C" * 240
        message = f"The computer does not start.\n{blob}\n-- \n{blob}\nRegards"
        cleaned = text_for_model(message)
        self.assertEqual(
            cleaned,
            "The computer does not start.\n[attachment omitted]",
        )
        self.assertNotIn(blob, cleaned)
        self.assertNotIn("Regards", cleaned)

    def test_signature_only_uses_attachment_fallback(self) -> None:
        self.assertEqual(text_for_model("-- \nJan Nowak"), "[attachment omitted]")


if __name__ == "__main__":
    unittest.main()
