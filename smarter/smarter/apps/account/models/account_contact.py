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
- Automatically sends a welcome email to new contacts.
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

from typing import Optional

# django stuff
from django.db import models
from django.template.loader import render_to_string

# our stuff
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .account import Account, welcome_email_context

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


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

    def send_email(self, subject: str, body: str, html: bool = False, from_email: Optional[str] = None):
        """
        Send an email to this account contact.

        This method uses the Smarter email helper to deliver a message to the contact's email address.
        It supports both plain text and HTML emails, and allows customization of the sender address.

        :param subject: String. The email subject line.
        :param body: String. The email body content.
        :param html: Boolean. If True, sends the email as HTML. Defaults to False.
        :param from_email: String or None. Optional sender email address.

        .. note::

            If the contact is marked as a test contact (`is_test=True`), the email is sent quietly.

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

        email_helper.send_email(
            subject=subject, to=self.email, body=body, html=html, from_email=from_email, quiet=self.is_test
        )

    def send_welcome_email(self) -> None:
        """
        Send a personalized welcome email to this account contact.

        This method renders the welcome email template with the contact's first name and sends it as HTML.

        :returns: None

        .. note::

            The welcome email uses the template at ``account/email/welcome.html``.

        .. tip::

            This method is automatically called when a new contact is created and has not yet been welcomed.

        **Example usage**::

            contact.send_welcome_email()

        """
        context = welcome_email_context(first_name=self.first_name)
        html_template = render_to_string("account/email/welcome.html", context)
        logger.debug(
            "%s.send_welcome_email() Sending welcome email to %s",
            logging.formatted_text(__name__ + ".AccountContact.send_welcome_email()"),
            self.email,
        )

        subject = "Welcome to Smarter!"
        body = html_template
        self.send_email(subject=subject, body=body, html=True)

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
        prefix = logging.formatted_text(__name__ + ".AccountContact.send_email_to_primary_contact()")
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

    def save(self, *args, **kwargs):
        """
        Save the AccountContact instance, enforcing primary contact uniqueness and sending a welcome email if needed.

        This method ensures that only one primary contact exists per account. If the contact is new and has not
        been welcomed, a welcome email is sent and the `welcomed` flag is updated.

        :param args: Positional arguments passed to the parent save method.
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
        prefix = logging.formatted_text(__name__ + ".AccountContact.save()")
        logger.debug("%s called with args: %s, kwargs: %s", prefix, args, kwargs)
        if self.is_primary:
            # Check for another primary contact for this account (excluding self if updating)
            qs = AccountContact.objects.filter(account=self.account, is_primary=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise SmarterValueError("There is already a primary contact for this account.")

        super().save(*args, **kwargs)
        if not self.welcomed:
            self.send_welcome_email()
            self.welcomed = True
            self.save()

    def __str__(self):
        return self.first_name + " " + self.last_name
