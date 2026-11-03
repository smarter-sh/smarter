"""Mailchimp API helper functions."""

from typing import cast

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
from pydantic import SecretStr

from smarter.common.conf import smarter_settings
from smarter.lib import logging

logger = logging.getLogger(__name__)

MAILCHIMP_SERVER = "us3"


class MailchimpHelper:
    """Mailchimp API helper functions."""

    client = MailchimpMarketing.Client()
    # the default and the settings validator are both a SecretStr, so the setting is never None.
    mailchimp_api_key = cast(SecretStr, smarter_settings.mailchimp_api_key)
    client.set_config({"api_key": mailchimp_api_key.get_secret_value(), "server": MAILCHIMP_SERVER})

    def ping(self) -> bool:
        """
        Whether the MailChimp api answers a ping.

        :returns: True if it does.
        """
        try:
            mailchimp_api_response = self.client.ping.get()
            logger.debug("Connected to MailChimp API: %s", mailchimp_api_response)
            return True
        except ApiClientError as error:
            logger.error(
                "An error occurred while trying to communicate with MailChimp API: status %s %s",
                error.status_code,
                error.text,
            )
        return False

    def add_list_member(self, email_address) -> bool:
        """
        Subscribe an email address to the MailChimp list, ``smarter_settings.mailchimp_list_id``.

        :param email_address: The email address.
        :returns: True if MailChimp says it is subscribed.
        """

        # ------------------------------
        # Add to Mailchimp
        # https://mailchimp.com/developer/marketing/docs/fundamentals/
        # https://github.com/mailchimp/mailchimp-marketing-python
        # ------------------------------
        if not self.ping():
            return False
        try:
            mailchimp_api_response = self.client.lists.add_list_member(
                smarter_settings.mailchimp_list_id, {"email_address": email_address, "status": "subscribed"}
            )
            if mailchimp_api_response.get("status") == "subscribed":
                logger.debug(
                    "Added %s to list %s, response: %s",
                    email_address,
                    smarter_settings.mailchimp_list_id,
                    mailchimp_api_response,
                )
                return True
            logger.warning(
                "Failed to add %s to list %s, response: %s",
                email_address,
                smarter_settings.mailchimp_list_id,
                mailchimp_api_response,
            )
            return False
        except ApiClientError as error:
            logger.error(
                "An error occurred while trying to communicate with MailChimp API: status %s %s",
                error.status_code,
                error.text,
            )
            # Never log the API key itself.
            logger.error(
                "List ID: %s, Intended email addition: %s, MailChimp server: %s",
                smarter_settings.mailchimp_list_id,
                email_address,
                MAILCHIMP_SERVER,
            )
        return False
