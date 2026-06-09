"""Signals for llm_client app.

These signals are used to notify various events in the llm_client lifecycle,
such as deployment, DNS verification, and API management.
"""

from django.dispatch import Signal

llm_client_called = Signal()
"""
Signal triggered when an llm_client is called.

Arguments:
    llm_client (LLMClient): The llm_client instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    llm_client_called.send(sender=self.__class__, llm_client=self.llm_client, request=request, args=args, kwargs=kwargs)
"""

llm_client_dns_verification_initiated = Signal()
"""
Signal triggered when DNS verification is initiated for an llm_client.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_dns_verification_initiated.send(sender=self.__class__, llm_client=self)
"""

llm_client_dns_verified = Signal()
"""
Signal triggered when DNS verification is successful for an llm_client.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_dns_verified.send(sender=self.__class__, llm_client=self)
"""

llm_client_dns_failed = Signal()
"""
Signal triggered when DNS verification fails for an llm_client.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_dns_failed.send(sender=self.__class__, llm_client=self)
"""

llm_client_dns_verification_status_changed = Signal()
"""
Signal triggered when the DNS verification status changes for an llm_client.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_dns_verification_status_changed.send(sender=self.__class__, llm_client=self)
"""

llm_client_deploy = Signal()
"""
Signal triggered when an llm_client deployment is initiated.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_deploy.send(sender=self.__class__, llm_client=self)
"""


llm_client_deployed = Signal()
"""
Signal triggered when an llm_client is successfully deployed.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_deployed.send(sender=self.__class__, llm_client=self)
"""

llm_client_deploy_failed = Signal()
"""
Signal triggered when an llm_client deployment fails.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_deploy_failed.send(sender=self.__class__, llm_client=self)
"""

llm_client_deploy_status_changed = Signal()
"""
Signal triggered when the deployment status of an llm_client changes.

Arguments:
    llm_client (LLMClient): The llm_client instance.

Example::

    llm_client_deploy_status_changed.send(sender=self.__class__, llm_client=self)
"""
llm_client_undeploy = Signal()

# tasks
pre_verify_certificate = Signal()
"""
Signal triggered before verifying a certificate.

Arguments:
    certificate_arn (str): The ARN of the certificate to be verified.

Example::

    pre_verify_certificate.send(sender=verify_certificate, certificate_arn=certificate_arn)
"""
pre_create_llm_client_request = Signal()
"""
Signal triggered before creating an llm_client request.

Arguments:
    llm_client_id (int): The ID of the llm_client.
    request_data (dict): The data for the llm_client request.

Example::

    pre_create_llm_client_request.send(sender=create_llm_client_request, llm_client_id=llm_client_id, request_data=request_data)
"""

pre_register_custom_domain = Signal()
"""
Signal triggered before registering a custom domain.

Arguments:
    account_id (int): The ID of the account.
    domain_name (str): The name of the domain to be registered.

Example::

    pre_register_custom_domain.send(sender=register_custom_domain, account_id=account_id, domain_name=domain_name)
"""

pre_create_custom_domain_dns_record = Signal()
"""
Signal triggered before creating a DNS record for a custom domain.

Arguments:
    llm_client_custom_domain_id (int): The ID of the llm_client custom domain.
    record_name (str): The name of the DNS record.
    record_type (str): The type of the DNS record (e.g., A, CNAME).
    record_value (str): The value of the DNS record.
    record_ttl (int): The TTL (time to live) for the DNS record.

Example::

        pre_create_custom_domain_dns_record.send(
            sender=create_custom_domain_dns_record,
            llm_client_custom_domain_id=llm_client_custom_domain_id,
            record_name=record_name,
            record_type=record_type,
            record_value=record_value,
            record_ttl=record_ttl,
        )
"""
pre_verify_custom_domain = Signal()
"""
Signal triggered before verifying a custom domain.

Arguments:
    hosted_zone_id (str): The ID of the hosted zone for the custom domain.

Example::

    pre_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id)
"""

pre_verify_domain = Signal()
"""
Signal triggered before verifying a domain.

Arguments:
    domain_name (str): The name of the domain to be verified.
    record_type (str): The type of DNS record used for verification.

Example::

    pre_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type)
"""

pre_destroy_domain_A_record = Signal()
"""
Signal triggered before destroying a domain's A record.

Arguments:
    hostname (str): The hostname of the domain.
    api_host_domain (str): The API host domain associated with the A record.

Example::

    pre_destroy_domain_A_record.send(sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain)
"""

pre_deploy_default_api = Signal()
"""
Signal triggered before deploying the default API.

Arguments:
    llm_client_id (int): The ID of the llm_client.
    with_domain_verification (bool): Flag indicating whether to include domain verification.

Example::

    pre_deploy_default_api.send(
        sender=deploy_default_api, llm_client_id=llm_client_id, with_domain_verification=with_domain_verification
    )
"""

pre_undeploy_default_api = Signal()
"""
Signal triggered before undeploying the default API.

Arguments:
    llm_client_id (int): The ID of the llm_client.

Example::

    pre_undeploy_default_api.send(sender=undeploy_default_api, llm_client_id=llm_client_id)
"""

pre_delete_default_api = Signal()
"""
Signal triggered before deleting the default API.

Arguments:
    url (str): The URL of the default API to be deleted.
    account_number (str): The account number associated with the default API.
    name (str): The name of the default API.

Example::

    pre_delete_default_api.send(sender=delete_default_api, url=url, account_number=account_number, name=name)
"""

pre_deploy_custom_api = Signal()
"""
Signal triggered before deploying a custom API.

Arguments:
    llm_client_id (int): The ID of the llm_client.

Example::

    pre_deploy_custom_api.send(sender=deploy_custom_api, llm_client_id=llm_client_id)
"""

post_verify_certificate = Signal()
"""
Signal triggered after verifying a certificate.

Arguments:
    certificate_arn (str): The ARN of the verified certificate.

Example::

    post_verify_certificate.send(sender=verify_certificate, certificate_arn=certificate_arn)
"""

post_create_llm_client_request = Signal()
"""
Signal triggered after creating an llm_client request.

Arguments:
    llm_client_id (int): The ID of the llm_client.
    request_data (dict): The data for the llm_client request.

Example::

    post_create_llm_client_request.send(sender=create_llm_client_request, llm_client_id=llm_client_id, request_data=request_data)
"""

post_register_custom_domain = Signal()
"""
Signal triggered after registering a custom domain.

Arguments:
    account_id (int): The ID of the account.
    domain_name (str): The name of the registered domain.

Example::

    post_register_custom_domain.send(sender=register_custom_domain, account_id=account_id, domain_name=domain_name)
"""
post_create_custom_domain_dns_record = Signal()
"""
Signal triggered after creating a DNS record for a custom domain.

Arguments:
    llm_client_custom_domain_id (int): The ID of the llm_client custom domain.
    record_name (str): The name of the DNS record.
    record_type (str): The type of the DNS record (e.g., A, CNAME).
    record_value (str): The value of the DNS record.
    record_ttl (int): The TTL (time to live) for the DNS record.

Example::

        post_create_custom_domain_dns_record.send(
            sender=create_custom_domain_dns_record,
            llm_client_custom_domain_id=llm_client_custom_domain_id,
            record_name=record_name,
            record_type=record_type,
            record_value=record_value,
            record_ttl=record_ttl,
        )
"""
post_verify_custom_domain = Signal()
"""
Signal triggered after verifying a custom domain.

Arguments:
    hosted_zone_id (str): The ID of the hosted zone for the custom domain.

Example::

    post_verify_custom_domain.send(sender=verify_custom_domain, hosted_zone_id=hosted_zone_id)
"""

post_verify_domain = Signal()
"""
Signal triggered after verifying a domain.

Arguments:
    domain_name (str): The name of the domain to be verified.
    record_type (str): The type of DNS record used for verification.

Example::

    post_verify_domain.send(sender=verify_domain, domain_name=domain_name, record_type=record_type)
"""

post_destroy_domain_A_record = Signal()
"""
Signal triggered after destroying a domain's A record.

Arguments:
    hostname (str): The hostname of the domain.
    api_host_domain (str): The API host domain associated with the A record.

Example::

        post_destroy_domain_A_record.send(
            sender=destroy_domain_A_record, hostname=hostname, api_host_domain=api_host_domain
        )
"""

post_deploy_default_api = Signal()
"""
Signal triggered after deploying the default API.

Arguments:
    llm_client_id (int): The ID of the llm_client.
    with_domain_verification (bool): Flag indicating whether domain verification was included.

Example::

        post_deploy_default_api.send(
            sender=deploy_default_api, llm_client_id=llm_client_id, with_domain_verification=with_domain_verification
        )
"""

post_undeploy_default_api = Signal()
"""
Signal triggered after undeploying the default API.

Arguments:
    llm_client_id (int): The ID of the llm_client.

Example::

    post_undeploy_default_api.send(sender=undeploy_default_api, llm_client_id=llm_client_id)
"""

post_delete_default_api = Signal()
"""
Signal triggered after deleting the default API.

Arguments:
    url (str): The URL of the deleted default API.
    account_number (str): The account number associated with the default API.
    name (str): The name of the default API.

Example::

    post_delete_default_api.send(sender=delete_default_api, url=url, account_number=account_number, name=name)
"""

post_deploy_custom_api = Signal()
"""
Signal triggered after deploying a custom API.

Arguments:
    llm_client_id (int): The ID of the llm_client.

Example::

    post_deploy_custom_api.send(sender=deploy_custom_api, llm_client_id=llm_client_id)
"""

broker_ready = Signal()
"""
Signal sent when a broker achieves a ready state.

Arguments:
    broker: The broker instance that is ready.

Example::

    broker_ready.send(sender=self.__class__, broker=self)
"""
