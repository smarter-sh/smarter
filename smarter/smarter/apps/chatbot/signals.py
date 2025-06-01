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

# tasks
pre_verify_certificate = Signal()
pre_create_chatbot_request = Signal()
pre_register_custom_domain = Signal()
pre_create_custom_domain_dns_record = Signal()
pre_verify_custom_domain = Signal()
pre_verify_domain = Signal()
pre_destroy_domain_A_record = Signal()
pre_deploy_default_api = Signal()
pre_undeploy_default_api = Signal()
pre_delete_default_api = Signal()
pre_deploy_custom_api = Signal()

post_verify_certificate = Signal()
post_create_chatbot_request = Signal()
post_register_custom_domain = Signal()
post_create_custom_domain_dns_record = Signal()
post_verify_custom_domain = Signal()
post_verify_domain = Signal()
post_destroy_domain_A_record = Signal()
post_deploy_default_api = Signal()
post_undeploy_default_api = Signal()
post_delete_default_api = Signal()
post_deploy_custom_api = Signal()
