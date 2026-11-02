"""
Account Contact Models
======================

This module defines the :class:`AccountContact` model, which manages contact information associated with accounts.
Unlike the standard Django User model, `AccountContact` allows for the management of email lists and contact details
independently from registered users. This is useful for sending communications to non-user contacts or users who opt out of system emails.

Classes
-------

- :class:`AccountContact`: Stores contact details for accounts, supports primary/test contacts, and provides email utilities.

Key Features
------------

- Enforces a single primary contact per account.
- Supports sending emails to individual contacts, all contacts, or just the primary contact.
- Automatically sends a welcome email to new contacts, and records when it was sent.
- Sends the Slack invitation email, which a Celery Beat task sends two days after the welcome email.
- Lets an email address unsubscribe from both emails, with a signed link in each of them.
- Integrates with Smarter's logging and email helper utilities.

Example
-------

.. code-block:: python

    from smarter.apps.account.models import AccountContact
    contact = AccountContact.objects.create(
        account=account,
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        is_primary=True
    )
    contact.send_welcome_email()
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from urllib.parse import urljoin

# django stuff
from django.conf import settings
from django.core import signing
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy

# our stuff
from smarter.apps.account.const import SLACK_INVITATION_EMAIL_DELAY
from smarter.apps.infrastructure.services import infrastructure
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .account import Account, welcome_email_context

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def welcome_email_languages() -> list[str]:
    """
    Return the language codes in which the welcome email can be sent.

    These are the codes of ``settings.LANGUAGES``, e.g. ``en``, ``es``, ``fr`` and ``pt-br``.
    The ``--language`` option of the management commands that send the welcome email offers them.

    :returns: The language codes, in the order of ``settings.LANGUAGES``.
    """
    return [code for code, _ in settings.LANGUAGES]


UNSUBSCRIBE_SALT = "smarter.apps.account.models.account_contact.unsubscribe"
"""The salt of the signed unsubscribe tokens, which keeps them from being valid as any other signed value."""


@dataclass(frozen=True)
class ContactEmail:
    """
    An HTML email that account contacts are sent, and can unsubscribe from.

    :param name: What the email is, for log messages, e.g. ``welcome``.
    :param template_name: The template of its body, e.g. ``account/email/welcome.html``.
    :param subject: Its subject, marked for translation with ``gettext_lazy``, so that it is
        translated into the language that the email is sent in.
    """

    name: str
    template_name: str
    subject: Union[str, Promise]


WELCOME_EMAIL = ContactEmail(
    name="welcome",
    template_name="account/email/welcome.html",
    subject=gettext_lazy("Welcome to Smarter!"),
)
"""The welcome email, which a new :class:`AccountContact` is sent when it is saved."""

SLACK_INVITATION_EMAIL = ContactEmail(
    name="Slack invitation",
    template_name="account/email/slack-invitation.html",
    subject=gettext_lazy("Join the Smarter community on Slack"),
)
"""The Slack invitation email, which :meth:`AccountContact.send_slack_invitation_emails` sends."""


def unsubscribe_token(email: str) -> str:
    """
    Return the signed token of an email address's unsubscribe link.

    The token never expires, so that the link in an old email still works, and is the same every
    time for the same address. It is signed with ``settings.SECRET_KEY``, so that nobody can
    unsubscribe someone else's address.

    :param email: The email address.
    :returns: The token, which is safe in a url path.
    """
    return signing.Signer(salt=UNSUBSCRIBE_SALT).sign_object(email.strip().lower())


def unsubscribe_email_address(token: str) -> str:
    """
    Return the email address of an unsubscribe token.

    :param token: A token that :func:`unsubscribe_token` made.
    :returns: The email address, in lower case.
    :raises django.core.signing.BadSignature: If the token was not signed by this platform, or was changed.
    """
    return str(signing.Signer(salt=UNSUBSCRIBE_SALT).unsign_object(token))


def unsubscribe_url(email: str) -> str:
    """
    Return the absolute url of an email address's unsubscribe page.

    :param email: The email address.
    :returns: The url, on the platform's domain, e.g.
        ``https://platform.example.com/account/unsubscribe/<token>/``.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.urls import AccountReverseNames
    from smarter.lib.django.shortcuts import reverse

    path = reverse(
        f"{AccountReverseNames.namespace}:{AccountReverseNames.unsubscribe}",
        kwargs={"token": unsubscribe_token(email)},
        urlconf=settings.ROOT_URLCONF,
    )
    url = urljoin(smarter_settings.environment_url, path)
    return SmarterValidator.urlify(url, environment=smarter_settings.environment)


def contact_email_context(first_name: str, email: str) -> SmarterDictType:
    """
    Return the context of a :class:`ContactEmail`'s template.

    It is :func:`~smarter.apps.account.models.welcome_email_context`, plus the recipient's
    ``unsubscribe_url``, which the footer of every contact email links to.

    :param first_name: The recipient's first name, or an empty string.
    :param email: The recipient's email address.
    :returns: The context.
    """
    context = welcome_email_context(first_name=first_name)
    context["unsubscribe_url"] = unsubscribe_url(email)
    return context


# pylint: disable=too-many-arguments
def send_contact_email(
    contact_email: ContactEmail,
    email: str,
    first_name: str = "",
    language: Optional[str] = None,
    quiet: bool = False,
) -> bool:
    """
    Send a :class:`ContactEmail` to an email address, unless the address unsubscribed.

    The address doesn't need to belong to an :class:`AccountContact`, so that the
    ``send_slack_invitation_email`` management command can send the Slack invitation to
    anyone. The email has ``List-Unsubscribe`` headers (RFC 8058), so that mail clients show
    their own unsubscribe button, which posts to the same page as the link in the footer.

    :param contact_email: The email to send, e.g. :data:`WELCOME_EMAIL`.
    :param email: The recipient's email address.
    :param first_name: The recipient's first name, for the greeting. Empty for a generic greeting.
    :param language: A language code of ``settings.LANGUAGES``. Defaults to ``settings.LANGUAGE_CODE``.
    :param quiet: True to only log what would have been sent, e.g. for a test contact.
    :returns: True if the email was sent.
    :raises SmarterValueError: If the language is not one of ``settings.LANGUAGES``.
    """
    prefix = logging.SmarterFormattedText.text(__name__) + ".send_contact_email()"
    language = language or settings.LANGUAGE_CODE
    if language not in welcome_email_languages():
        raise SmarterValueError(f"Unknown language {language}. Choose one of {', '.join(welcome_email_languages())}.")
    unsubscribed_at = AccountContact.unsubscribed_at_of(email)
    if unsubscribed_at:
        logger.info(
            "%s Not sending the %s email to %s, who unsubscribed on %s",
            prefix,
            contact_email.name,
            email,
            unsubscribed_at.isoformat(),
        )
        return False
    with translation.override(language):
        context = contact_email_context(first_name=first_name, email=email)
        body = render_to_string(contact_email.template_name, context)
        subject = str(contact_email.subject)
    logger.debug("%s Sending the %s %s email to %s", prefix, language, contact_email.name, email)
    return infrastructure.email.send_email(
        subject=subject,
        to=email,
        body=body,
        html=True,
        quiet=quiet,
        headers={
            "List-Unsubscribe": f"<{context['unsubscribe_url']}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )


class AccountContact(TimestampedModel):
    """
    Model for storing contact information associated with an account.

    Unlike the User model, `AccountContact` allows management of email lists and contact details
    independently from registered users. This is useful for sending communications to non-user contacts,
    or for users who opt out of system emails.

    :param account: ForeignKey to :class:`Account`. The related account.
    :param first_name: String. Contact's first name.
    :param last_name: String. Contact's last name.
    :param email: String. Contact's email address.
    :param phone: String. Contact's phone number (optional).
    :param is_primary: Boolean. Marks this contact as the primary contact for the account.
    :param is_test: Boolean. Indicates if this contact is for testing purposes.
    :param welcomed: Boolean. Indicates if a welcome email has been sent.
    :param welcomed_at: DateTime or None. When the welcome email was sent.
    :param slack_invited_at: DateTime or None. When the Slack invitation email was sent.
    :param unsubscribed_at: DateTime or None. When the contact's email address unsubscribed from the
        welcome and Slack invitation emails.

    .. note::

        Contacts do not need to be registered users.

    .. tip::

        Use :meth:`send_email_to_account` to broadcast messages to all contacts.

    .. attention::

        Only one primary contact is allowed per account.

    **Example usage**::

        from smarter.apps.account.models import AccountContact
        contact = AccountContact.objects.create(
            account=account,
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            is_primary=True
        )

    .. seealso::

        :class:`Account`, :class:`UserProfile`
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Account Contact"
        verbose_name_plural = "Account Contacts"
        unique_together = ("account", "email")

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="contacts")
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Indicates if this contact is the primary contact for the account. Only one contact can be primary per account.",
    )
    is_test = models.BooleanField(
        default=False, help_text="Indicates if this contact is used for unit testing purposes."
    )
    welcomed = models.BooleanField(
        default=False, help_text="Indicates if a welcome email has been sent to this contact."
    )
    welcomed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the welcome email was sent to this contact. Empty if it was never sent.",
    )
    slack_invited_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the Slack invitation email was sent to this contact's email address. Empty if it was never sent.",
    )
    unsubscribed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When this contact's email address unsubscribed from the welcome and Slack invitation emails. Empty while subscribed.",
    )

    def send_email(self, subject: str, body: str, html: bool = False, from_email: Optional[str] = None) -> bool:
        """
        Send an email to this account contact.

        This method uses the Smarter email helper to deliver a message to the contact's email address.
        It supports both plain text and HTML emails, and allows customization of the sender address.

        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.
        :returns: True if the email was sent.

        .. note::

            If the contact is marked as a test contact (`is_test=True`), the email is sent quietly.

        .. note::

            This sends account notices, which an unsubscribed contact still receives. Only the
            :class:`ContactEmail` emails respect :attr:`unsubscribed_at`.

        .. tip::

            Use this method for direct, transactional communications with account contacts.

        **Example usage**::

            contact.send_email(
                subject="Welcome!",
                body="Hello and welcome to Smarter.",
                html=True,
                from_email="support@smarter.com"
            )
        """

        return infrastructure.email.send_email(
            subject=subject, to=self.email, body=body, html=html, from_email=from_email, quiet=self.is_test
        )

    def preferred_language(self) -> str:
        """
        Return the language in which this contact is sent emails.

        This is the :attr:`UserProfile.language <smarter.apps.account.models.UserProfile.language>` of the
        account's user who has the contact's email address, or ``settings.LANGUAGE_CODE`` (English) for a
        contact who isn't a user of the account.

        :returns: A language code of ``settings.LANGUAGES``, e.g. ``en`` or ``es``.
        """
        language = self.account.user_profiles.filter(user__email=self.email).values_list("language", flat=True).first()
        return language or settings.LANGUAGE_CODE

    def send_welcome_email(self, language: Optional[str] = None) -> bool:
        """
        Send a personalized welcome email to this account contact.

        This method renders the welcome email template with the contact's first name, in the
        given language, and sends it as HTML, unless the contact's email address unsubscribed.
        When it is sent, :attr:`welcomed_at` records when, and the Slack invitation email follows
        two days later.

        :param language: String or None. A language code of ``settings.LANGUAGES``, e.g. ``es`` or
            ``pt-br``. Defaults to :meth:`preferred_language`.
        :returns: True if the email was sent.
        :raises SmarterValueError: If the language is not one of ``settings.LANGUAGES``.

        .. note::

            The welcome email uses the template at ``account/email/welcome.html``, and its
            translations in the ``django`` message catalogs.

        .. tip::

            This method is automatically called when a new contact is created and has not yet been welcomed.

        **Example usage**::

            contact.send_welcome_email()
            contact.send_welcome_email(language="es")
        """
        sent = send_contact_email(
            WELCOME_EMAIL,
            email=self.email,
            first_name=self.first_name,
            language=language or self.preferred_language(),
            quiet=self.is_test,
        )
        if sent:
            self.welcomed_at = timezone.now()
            if self.pk:
                AccountContact.objects.filter(pk=self.pk).update(welcomed_at=self.welcomed_at)
        return sent

    def send_slack_invitation_email(self, language: Optional[str] = None) -> bool:
        """
        Send the Slack invitation email to this account contact.

        The email invites the contact to the Slack workspace of ``smarter_settings.branding_url_slack``,
        unless the contact's email address unsubscribed. When it is sent, :attr:`slack_invited_at`
        records when, on every contact with the same email address, so that a person who is a
        contact of several accounts is invited once.

        :param language: String or None. A language code of ``settings.LANGUAGES``. Defaults to
            :meth:`preferred_language`.
        :returns: True if the email was sent.
        :raises SmarterValueError: If the language is not one of ``settings.LANGUAGES``.

        **Example usage**::

            contact.send_slack_invitation_email(language="fr")
        """
        sent = send_contact_email(
            SLACK_INVITATION_EMAIL,
            email=self.email,
            first_name=self.first_name,
            language=language or self.preferred_language(),
            quiet=self.is_test,
        )
        if sent:
            self.slack_invited_at = timezone.now()
            AccountContact.objects.filter(email__iexact=self.email).update(slack_invited_at=self.slack_invited_at)
        return sent

    @classmethod
    def due_slack_invitations(cls, now: Optional[datetime] = None) -> "models.QuerySet[AccountContact]":
        """
        Return the contacts who are due the Slack invitation email.

        They were sent the welcome email at least ``SLACK_INVITATION_EMAIL_DELAY`` (two days) ago,
        and were neither sent the Slack invitation nor unsubscribed. Test contacts are never due.
        Contacts who were welcomed before :attr:`welcomed_at` existed have no date, and are never due.

        :param now: The current time. Defaults to ``timezone.now()``.
        :returns: The contacts, the longest-welcomed first.
        """
        now = now or timezone.now()
        return cls.objects.filter(
            welcomed_at__lte=now - SLACK_INVITATION_EMAIL_DELAY,
            slack_invited_at__isnull=True,
            unsubscribed_at__isnull=True,
            is_test=False,
        ).order_by("welcomed_at", "pk")

    @classmethod
    def send_slack_invitation_emails(cls) -> int:
        """
        Send the Slack invitation email to every contact who is due it.

        The Celery Beat task :func:`smarter.apps.account.tasks.send_slack_invitation_emails` calls
        this hourly. Each email address is sent one email, even if it is the address of several
        contacts. Before sending, the address's contacts are claimed, by setting their
        :attr:`slack_invited_at`, so that two runs at once can't both send it. If the email isn't
        sent, the claim is released, and the next run tries again.

        :returns: The number of emails sent.
        """
        prefix = logging.SmarterFormattedText.text(__name__) + ".AccountContact.send_slack_invitation_emails()"
        now = timezone.now()
        sent_count = 0
        addresses: set[str] = set()
        for contact in cls.due_slack_invitations(now):
            address = contact.email.strip().lower()
            if address in addresses:
                continue
            addresses.add(address)
            claimed = cls.objects.filter(email__iexact=address, slack_invited_at__isnull=True).update(
                slack_invited_at=now
            )
            if not claimed:
                continue
            sent = False
            try:
                sent = contact.send_slack_invitation_email()
            finally:
                if not sent:
                    cls.objects.filter(email__iexact=address, slack_invited_at=now).update(slack_invited_at=None)
            if sent:
                sent_count += 1
        logger.info("%s sent %s Slack invitation emails.", prefix, sent_count)
        return sent_count

    @classmethod
    def unsubscribed_at_of(cls, email: str) -> Optional[datetime]:
        """
        Return when an email address unsubscribed from the welcome and Slack invitation emails.

        :param email: The email address, in any case.
        :returns: The earliest :attr:`unsubscribed_at` of the address's contacts, or None if it is subscribed.
        """
        return (
            cls.objects.filter(email__iexact=email.strip(), unsubscribed_at__isnull=False)
            .order_by("unsubscribed_at")
            .values_list("unsubscribed_at", flat=True)
            .first()
        )

    @classmethod
    def unsubscribe(cls, email: str) -> int:
        """
        Unsubscribe an email address from the welcome and Slack invitation emails.

        Every contact with the address, in every account, records the time in :attr:`unsubscribed_at`.
        A contact that is added later with the same address is unsubscribed when it is saved.

        :param email: The email address, in any case.
        :returns: The number of contacts that were unsubscribed: 0 if the address has no contact, or
            was already unsubscribed.
        """
        count = cls.objects.filter(email__iexact=email.strip(), unsubscribed_at__isnull=True).update(
            unsubscribed_at=timezone.now()
        )
        logger.info(
            "%s unsubscribed %s contacts with the email address %s.",
            logging.SmarterFormattedText.text(__name__) + ".AccountContact.unsubscribe()",
            count,
            email,
        )
        return count

    @classmethod
    def get_primary_contact(cls, account: Account) -> Optional["AccountContact"]:
        """
        Retrieve the primary contact for a given account.

        This method returns the first contact marked as primary for the specified account, or None if no such contact exists.

        :param account: Instance of :class:`Account`. The account to search for a primary contact.
        :returns: Optional[AccountContact]
            The primary contact instance, or None if not found.

        .. tip::

            Use this method to quickly access the main point of contact for notifications or support.

        **Example usage**::

            primary_contact = AccountContact.get_primary_contact(account)
            if primary_contact:
                print(primary_contact.email)
        """
        return cls.objects.filter(account=account, is_primary=True).first()

    # pylint: disable=too-many-arguments
    @classmethod
    def send_email_to_account(
        cls, account: Account, subject: str, body: str, html: bool = False, from_email: Optional[str] = None
    ) -> None:
        """
        Send an email to all contacts associated with a given account.

        This method iterates over all contacts for the specified account and sends the provided message
        to each contact's email address.

        :param account: Instance of :class:`Account`. The account whose contacts will receive the email.
        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.

        .. note::

            Contacts marked as test contacts (`is_test=True`) will receive emails quietly.

        .. tip::

            Use this method for account-wide notifications or announcements.

        **Example usage**::

            AccountContact.send_email_to_account(
                account=account,
                subject="System Update",
                body="We have updated our terms of service.",
                html=False
            )
        """
        contacts = cls.objects.filter(account=account)
        for contact in contacts:
            contact.send_email(subject=subject, body=body, html=html, from_email=from_email)

    # pylint: disable=too-many-arguments
    @classmethod
    def send_email_to_primary_contact(
        cls, account: Account, subject: str, body: str, html: bool = False, from_email: Optional[str] = None
    ) -> None:
        """
        Send an email to the primary contact of a given account.

        This method locates the primary contact for the specified account and sends the provided message.
        If no primary contact exists, an error is logged.

        :param account: Instance of :class:`Account`. The account whose primary contact will receive the email.
        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.

        .. attention::

            If no primary contact is found, no email is sent and an error is logged.

        .. tip::

            Use this method for urgent or important communications that require a single point of contact.

        **Example usage**::

            AccountContact.send_email_to_primary_contact(
                account=account,
                subject="Urgent: Action Required",
                body="Please review your account settings.",
                html=True
            )
        """
        prefix = logging.SmarterFormattedText.text(__name__) + ".AccountContact.send_email_to_primary_contact()"
        contact = cls.get_primary_contact(account)
        logger.debug(
            "%s.send_email_to_primary_contact() Attempting to send email to primary contact for account %s. Found contact: %s, subject: %s, body: %s, html: %s, from_email: %s",
            prefix,
            account,
            contact,
            subject,
            body,
            html,
            from_email,
        )
        if contact:
            contact.send_email(subject=subject, body=body, html=html, from_email=from_email)
        else:
            logger.error(
                "%s.send_email_to_primary_contact() No primary contact found for account %s",
                prefix,
                account,
            )

    def save(self, *args, language: Optional[str] = None, **kwargs):
        """
        Save the AccountContact instance, enforcing primary contact uniqueness and sending a welcome email if needed.

        This method ensures that only one primary contact exists per account. If the contact is new and has not
        been welcomed, a welcome email is sent and the `welcomed` flag is updated. A new contact
        whose email address unsubscribed is unsubscribed too, and isn't sent the welcome email.

        :param args: Positional arguments passed to the parent save method.
        :param language: String or None. The language of the welcome email, if one is sent. Defaults to
            :meth:`preferred_language`. See :meth:`send_welcome_email`.
        :param kwargs: Keyword arguments passed to the parent save method.

        .. attention::

            Only one contact per account can be marked as primary. Attempting to save another will raise an error.

        .. note::

            The welcome email is sent automatically for new contacts who have not been welcomed.

        :raises SmarterValueError: If another primary contact already exists for the account.

        **Example usage**::

            contact = AccountContact(account=account, email="jane@example.com", is_primary=True)
            contact.save()  # Ensures uniqueness and sends welcome email if needed
        """
        prefix = logging.SmarterFormattedText.text(__name__) + ".AccountContact.save()"
        logger.debug("%s called with args: %s, kwargs: %s", prefix, args, kwargs)
        if self.is_primary:
            # Check for another primary contact for this account (excluding self if updating)
            qs = AccountContact.objects.filter(account=self.account, is_primary=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise SmarterValueError("There is already a primary contact for this account.")

        # a new contact of an address that unsubscribed is unsubscribed too.
        if self._state.adding and self.unsubscribed_at is None:
            self.unsubscribed_at = AccountContact.unsubscribed_at_of(self.email)

        super().save(*args, **kwargs)
        if not self.welcomed:
            self.send_welcome_email(language=language)
            self.welcomed = True
            self.save()

    def __str__(self) -> str:
        return self.first_name + " " + self.last_name
