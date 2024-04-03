# -*- coding: utf-8 -*-
"""Mailchimp API helper functions"""

import logging

import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError

from smarter.common.conf import settings as smarter_settings


logger = logging.getLogger(__name__)

MAILCHIMP_SERVER = "us3"


class MailchimpHelper:
    """Mailchimp API helper functions"""

    client = MailchimpMarketing.Client()
    client.set_config({"api_key": smarter_settings.mailchimp_api_key, "server": MAILCHIMP_SERVER})

    def ping(self) -> bool:
        try:
            mailchimp_api_response = self.client.ping.get()
            logger.info("Connected to MailChimp API: %s", mailchimp_api_response)
            return True
        except ApiClientError as error:
            logger.error(
                "An error occurred while trying to communicate with MailChimp API: status %s %s",
                error.status_code,
                error.text,
            )
        return False

    def add_list_member(self, email_address) -> bool:

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
                logger.info(
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
            logger.error(
                "API key: %s, List ID: %s, Intended email addition: %s, MailChimp server: %s",
                smarter_settings.mailchimp_api_key,
                smarter_settings.mailchimp_list_id,
                email_address,
                MAILCHIMP_SERVER,
            )
        return False
