import unittest

from app.departments import Department
from app.mailer import build_message


class BuildMessageTest(unittest.TestCase):
    def test_it_goes_to_it_and_keeps_reply_to(self) -> None:
        message = build_message(
            department=Department.IT,
            reply_to="jan.nowak@example.com",
            subject="Awaria",
            body="Nie działa mi komputer",
        )

        self.assertEqual(message["To"], "it@example.com")
        self.assertEqual(message["Reply-To"], "jan.nowak@example.com")
        self.assertEqual(message["Subject"], "Awaria")

    def test_every_department_has_the_brief_address(self) -> None:
        expected = {
            Department.KADRY: "kadry@example.com",
            Department.HUMAN_RESOURCES: "human-resources@example.com",
            Department.IT: "it@example.com",
            Department.HELP_DESK: "help-desk@example.com",
            Department.OTHER: "other@example.com",
        }
        for department, address in expected.items():
            message = build_message(
                department=department,
                reply_to="nadawca@example.com",
                subject="Test",
                body="Treść",
            )
            self.assertEqual(message["To"], address)


if __name__ == "__main__":
    unittest.main()
