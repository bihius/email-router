import os
import smtplib
from email.message import EmailMessage

from app.departments import DEPARTMENT_EMAIL, Department


def build_message(
    *,
    department: Department,
    reply_to: str,
    subject: str,
    body: str,
) -> EmailMessage:
    """Build an email message without sending it.

    Kept separate so headers can be asserted without MailHog running.
    """
    message = EmailMessage()
    message["From"] = os.environ.get("MAIL_FROM", "router@example.com")
    message["To"] = DEPARTMENT_EMAIL[department]
    message["Reply-To"] = reply_to
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_email(
    *,
    department: Department,
    reply_to: str,
    subject: str,
    body: str,
) -> None:
    """Send a message to the MailHog SMTP listener.

    From a laptop use localhost. From the future API container use host mailhog.
    """
    message = build_message(
        department=department,
        reply_to=reply_to,
        subject=subject,
        body=body,
    )
    host = os.environ.get("SMTP_HOST", "localhost")
    port = int(os.environ.get("SMTP_PORT", "1025"))
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.send_message(message)
