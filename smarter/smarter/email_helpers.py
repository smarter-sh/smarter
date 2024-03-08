# -*- coding: utf-8 -*-
"""Helper class for sending email via AWS Simple Email Service using SMTP."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings


class EmailHelper:
    """Helper class for sending emails."""

    @staticmethod
    def send_email(subject, body, to, html=False, from_email=None):
        """Send an email."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or settings.SMTP_FROM_EMAIL
        msg["To"] = to

        part2 = MIMEText(body, "html") if html else MIMEText(body)
        msg.attach(part2)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
