import unittest

from app.departments import get_department
from app.mailer import build_message


class BuildMessageTest(unittest.TestCase):
    def test_it_goes_to_it_and_keeps_reply_to(self) -> None:
        message = build_message(
            department=get_department("it"),
            reply_to="jan.nowak@example.com",
            subject="Awaria",
            body="Nie działa mi komputer",
        )

        self.assertEqual(message["To"], "it@example.com")
        self.assertEqual(message["Reply-To"], "jan.nowak@example.com")
        self.assertEqual(message["Subject"], "Awaria")

    def test_every_department_has_the_brief_address(self) -> None:
        expected = {
            "kadry": "kadry@example.com",
            "human_resources": "human-resources@example.com",
            "it": "it@example.com",
            "help_desk": "help-desk@example.com",
            "other": "other@example.com",
        }
        for name, address in expected.items():
            message = build_message(
                department=get_department(name),
                reply_to="nadawca@example.com",
                subject="Test",
                body="Treść",
            )
            self.assertEqual(message["To"], address)


if __name__ == "__main__":
    unittest.main()
