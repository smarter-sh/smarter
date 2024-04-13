# pylint: disable=W0613
"""
Stripe API integration for smarter account management.
see: https://dj-stripe.dev/dj-stripe/2.7/usage/webhooks/
"""

import logging

from django.db import transaction
from djstripe import webhooks


logger = logging.getLogger(__name__)


@webhooks.handler("customer")
def customer_event_handler(event, **kwargs):
    """Handle the customer event from Stripe."""
    logger.info("Customer event: %r", event)


@webhooks.handler("customer.subscription.trial_will_end")
def customer_subscription_trial_handler(event, **kwargs):
    """Handle the customer.subscription.trial_will_end event from Stripe."""
    logger.info("Customer subscription trial_will_end event: %r", event)


@webhooks.handler("price", "product")
def on_commit_handler(event, **kwargs):
    """
    Handle the price and product events from Stripe,
    once these have been committed.
    """

    def handle_event():
        """send a mail, invalidate a cache, fire off a Celery task, etc."""
        logger.info("event: %r", event)

    transaction.on_commit(handle_event)
