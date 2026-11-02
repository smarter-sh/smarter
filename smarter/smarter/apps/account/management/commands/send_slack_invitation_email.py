"""
Django management command to send the Slack invitation email to someone, now.

This module defines the ``send_slack_invitation_email`` management command for the Smarter platform.
The Celery Beat task ``smarter.apps.account.tasks.send_slack_invitation_emails`` sends the email to
every account contact two days after their welcome email. This command sends it ad hoc, to a user,
an account contact, or anyone else.

Features
--------
- Sends the HTML Slack invitation email to a user, by username or email address.
- Sends it to an email address that belongs to no user or account contact. Nothing is recorded
  for such an address.
- Records the time in ``AccountContact.slack_invited_at`` of every contact with the address, so
  that the Celery Beat task doesn't send it again.
- Refuses an address that was already invited, unless ``--force`` is given, and always refuses an
  address that unsubscribed.

Command-line Options
---------------------
- ``--username``: The username of the user.
- ``--email``: The email address, of a user, an account contact or anyone else.
- ``--first_name``: The first name in the greeting. Defaults to the user's or contact's first name.
- ``--language``: The language of the email, one of ``settings.LANGUAGES``, e.g. ``es``.
  Defaults to the user's preferred language (``UserProfile.language``), or English.
- ``--force``: Send it to an address that was already invited.

Typical Usage
-------------

.. code-block:: console

    python manage.py send_slack_invitation_email --username jdoe
    python manage.py send_slack_invitation_email --email jane@example.com --first_name Jane --language es
"""

from typing import Optional

from django.conf import settings
from django.core.management.base import CommandError
from django.utils import timezone

from smarter.apps.account.management.lookups import get_user
from smarter.apps.account.models import (
    SLACK_INVITATION_EMAIL,
    AccountContact,
    User,
    UserProfile,
    send_contact_email,
    welcome_email_languages,
)
from smarter.lib.django.management.base import SmarterCommand


# pylint: disable=E1101
class Command(SmarterCommand):
    """Send the html Slack invitation email to a user, an account contact, or any email address."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument("--username", type=str, help="The username")
        parser.add_argument("--email", type=str, help="The email address, of a user or of anyone else")
        parser.add_argument("--first_name", type=str, help="The first name in the greeting")
        parser.add_argument(
            "--language",
            type=str,
            choices=welcome_email_languages(),
            help="The language of the email. Default: the user's preferred language, or English",
        )
        parser.add_argument(
            "--force", action="store_true", help="Send the email to an address that was already invited"
        )

    @staticmethod
    def preferred_language(email: str) -> str:
        """
        Return the preferred language of the user with an email address.

        :param email: The email address.
        :returns: The user's ``UserProfile.language``, or ``settings.LANGUAGE_CODE`` for an address
            that is no user's.
        """
        language = UserProfile.objects.filter(user__email__iexact=email).values_list("language", flat=True).first()
        return language or settings.LANGUAGE_CODE

    def handle(self, *args, **options):
        """Send the Slack invitation email."""
        self.handle_begin()

        username: Optional[str] = options.get("username")
        email: Optional[str] = options.get("email")
        first_name: Optional[str] = options.get("first_name")
        language: Optional[str] = options.get("language")

        user: Optional[User] = None
        if username:
            user = get_user(username)
            email = email or user.email
        elif email:
            user = User.objects.filter(email__iexact=email).first()
        if not email:
            raise CommandError("Provide a --username, or an --email.")

        unsubscribed_at = AccountContact.unsubscribed_at_of(email)
        if unsubscribed_at:
            raise CommandError(f"{email} unsubscribed from these emails on {unsubscribed_at.isoformat()}.")

        contacts = AccountContact.objects.filter(email__iexact=email)
        invited_at = (
            contacts.filter(slack_invited_at__isnull=False)
            .order_by("slack_invited_at")
            .values_list("slack_invited_at", flat=True)
            .first()
        )
        if invited_at and not options.get("force"):
            raise CommandError(
                f"{email} was sent the Slack invitation email on {invited_at.isoformat()}. "
                "Add --force to send it again."
            )

        contact = contacts.first()
        if contact and not first_name:
            sent = contact.send_slack_invitation_email(language=language)
        else:
            if not first_name:
                first_name = user.first_name if user else ""
            sent = send_contact_email(
                SLACK_INVITATION_EMAIL,
                email=email,
                first_name=first_name,
                language=language or self.preferred_language(email),
            )
            if sent:
                contacts.update(slack_invited_at=timezone.now())

        if not sent:
            raise CommandError(f"The Slack invitation email was not sent to {email}. See the log for the reason.")
        self.handle_completed_success(f"Sent the Slack invitation email to {email}.")
