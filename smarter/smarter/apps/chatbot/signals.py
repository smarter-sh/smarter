"""Signals for account app."""

from django.dispatch import Signal


chatbot_called = Signal()
chatbot_dns_verification_initiated = Signal()
chatbot_dns_verified = Signal()
chatbot_dns_failed = Signal()
chatbot_dns_verification_status_changed = Signal()

chatbot_deployed = Signal()
chatbot_deploy_failed = Signal()
chatbot_deploy_status_changed = Signal()
chatbot_undeployed = Signal()
chatbot_deleted = Signal()
