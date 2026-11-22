# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The domains, urls, hosts and bucket names derived from :class:`PlatformSettings`."""

from functools import cached_property
from typing import List, Optional, Union
from urllib.parse import urlparse

from pydantic import Field, model_validator

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.settings.platform import PlatformSettings
from smarter.common.conf.util import (
    before_field_validator,
    comma_separated,
    field_default,
    input_value,
)
from smarter.common.const import (
    SMARTER_API_SUBDOMAIN,
    SMARTER_LOCAL_PORT,
    SmarterEnvironments,
)
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.django.validators import SmarterValidator


class DomainSettings(PlatformSettings):
    """The domains, urls, hosts and bucket names that are derived from the platform's identity."""

    allowed_hosts: List[str] = Field(
        ["localhost", "testserver"],
        description="The hosts that the platform serves: its own domains, and those set with SMARTER_ALLOWED_HOSTS.",
        examples=[["localhost", "testserver"]],
        title="Allowed Hosts",
    )
    """
    The host names that the platform serves, Django's ``ALLOWED_HOSTS``: its own domains, and the.

    hosts set with ``SMARTER_ALLOWED_HOSTS``, a comma-separated list.

    The platform's domains are always added: see :meth:`add_platform_hosts`. ``localhost`` and
    ``testserver`` are there for Kubernetes' liveness and readiness probes, and for Django's test
    client. Smarter's own middleware validates hosts as well: see
    :class:`smarter.apps.llmclient.middleware.security.SmarterSecurityMiddleware`.

    :type: List[str]
    :default: ``["localhost", "testserver"]``, plus the platform's domains
    """

    api_schema: str = Field(
        "http",
        description="The schema of the api's urls, http or https. Set with SMARTER_API_SCHEMA. Always http locally.",
        examples=["http", "https"],
        title="API Schema",
    )
    """
    The schema of the api's urls, ``http`` or ``https``.

    Set it with ``SMARTER_API_SCHEMA``. The local environment always uses ``http``, whatever it is set
    to: see :meth:`local_api_schema`.

    :type: str
    :default: ``"http"``
    :raises SmarterConfigurationError: If the value is neither ``http`` nor ``https``.
    """

    @before_field_validator("allowed_hosts")
    def validate_allowed_hosts(cls, v: Optional[Union[List[str], str]]) -> List[str]:
        """Validates the `allowed_hosts` field: a list, or a comma-separated string.

        Args:
            v: The hosts.
        Returns:
            List[str]: The hosts, or the default if it is empty.
        """
        if v in THE_EMPTY_SET:
            return list(field_default(cls, "allowed_hosts"))
        v = comma_separated(v)
        if not isinstance(v, list):
            raise SmarterConfigurationError(f"allowed_hosts of type {type(v)} is not a list.")
        return [str(host) for host in v]

    @before_field_validator("api_schema")
    def validate_api_schema(cls, v: Optional[str]) -> str:
        """Validates the `api_schema` field: ``http`` or ``https``, or the default if it is empty.

        Args:
            v (Optional[str]): The schema.
        Returns:
            str: The validated schema.
        """
        if v in THE_EMPTY_SET:
            return str(field_default(cls, "api_schema"))
        if not isinstance(v, str) or v.strip().lower() not in ("http", "https"):
            raise SmarterConfigurationError(f"api_schema {v} is neither http nor https.")
        return v.strip().lower()

    @model_validator(mode="before")
    @classmethod
    def local_api_schema(cls, data: object) -> object:
        """
        Use ``http`` for the api's urls in the local environment, which serves no https.

        :param data: The values to validate: the constructor's and the environment's.
        :returns: The values, with ``api_schema`` set to ``http`` in the local environment.
        """
        if not isinstance(data, dict):
            return data
        environment = input_value(cls, data, "environment")
        if environment != SmarterEnvironments.LOCAL:
            return data
        local = dict(data)
        local["api_schema"] = "http"
        return local

    @model_validator(mode="after")
    def add_platform_hosts(self) -> "DomainSettings":
        """
        Add the platform's own domains to :attr:`allowed_hosts`, so that it is the complete list.

        The domains, e.g. :attr:`environment_platform_domain`, are derived from the validated
        environment, root domain and subdomain, so they are added once those are validated. Each host
        with a port is added without it as well. Every host is validated.

        :returns: The settings, whose ``allowed_hosts`` is final.
        :raises SmarterConfigurationError: If a host is not a valid hostname.
        """
        hosts = [
            self.environment_platform_domain,
            self.environment_api_domain,
            f".{self.environment_api_domain}",
        ]
        for host in self.allowed_hosts:
            hosts.append(host)
        for host in list(hosts):
            parsed = urlparse(f"//{host}")
            if parsed.hostname and parsed.hostname not in hosts:
                hosts.append(parsed.hostname)
        for host in hosts:
            SmarterValidator.validate_hostname(host)
        unique_hosts = sorted(set(hosts))
        # the settings are frozen: this is the one place that completes a field after validation.
        object.__setattr__(self, "allowed_hosts", unique_hosts)
        return self

    @cached_property
    def environment_cdn_domain(self) -> str:
        """
        Return the CDN domain based on the environment domain.

        Examples:
            >>> print(smarter_settings.environment_cdn_domain)
            'cdn.alpha.platform.example.com'
            >>> print(smarter_settings.environment_cdn_domain)
            'cdn.localhost:9357'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
            - SmarterEnvironments()
        """
        if self.environment_is_local:
            # returns cdn.local.example.com
            return f"cdn.{SmarterEnvironments.LOCAL}.{self.platform_root_domain}"
        return f"cdn.{self.environment_platform_domain}"

    @cached_property
    def environment_cdn_url(self) -> str:
        """
        Return the CDN URL for the environment.

        Example:
            >>> print(smarter_settings.environment_cdn_url)
            https://cdn.alpha.platform.example.com
            >>> print(smarter_settings.environment_cdn_url)
            https://cdn.localhost:9357

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        Note:
            See https://github.com/smarter-sh/smarter-infrastructure for CDN setup details.
            Based on AWS CloudFront, AWS S3 and AWS Route 53. But, there are many details
            with regard to bucket policies, CNAME setup, SSL certificates, and so forth
            that are outside the scope of this comment. Please refer to the Terraform
            infrastructure repository for more information.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_cdn_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_cdn_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_cdn_domain: {self.environment_cdn_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def root_cdn_domain(self) -> str:
        """
        Return the CDN domain for the root domain.

        Example:
            >>> print(smarter_settings.root_cdn_domain)
            'cdn.example.com'
        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.platform_root_domain
        """
        return f"cdn.{self.platform_root_domain}"

    @cached_property
    def root_cdn_url(self) -> str:
        """
        Return the CDN URL for the root domain.

        Example:
            >>> print(smarter_settings.root_cdn_url)
            https://cdn.example.com
        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.
        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.root_cdn_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.root_cdn_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid root_cdn_domain: {self.root_cdn_domain}. " "Please check your environment settings."
            )
        return retval

    @cached_property
    def root_platform_domain(self) -> str:
        """
        Return the platform domain name for the root domain.

        Example:
            >>> print(smarter_settings.root_platform_domain)
            'platform.example.com'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.platform_root_domain
        """
        return f"{self.platform_subdomain}.{self.platform_root_domain}"

    @cached_property
    def root_proxy_domain(self) -> str:
        """
        Return the proxy domain name for the root domain.

        Used for proxying local requests inside of AWS Kubernetes environments
        during unit testing.

        Example:
            >>> print(smarter_settings.root_proxy_domain)
            'local.example.com'
        """
        return f"{SmarterEnvironments.LOCAL}.{self.platform_root_domain}"

    @cached_property
    def platform_url(self) -> str:
        """
        Return the platform URL for the root platform domain and environment.

        Example:
            >>> print(smarter_settings.platform_url)
            https://platform.example.com

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.root_platform_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.root_platform_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid root_platform_domain: {self.root_platform_domain}. " "Please check your environment settings."
            )
        return retval

    @cached_property
    def environment_platform_domain(self) -> str:
        """
        Return the complete domain name, including environment prefix if applicable.

        Examples:
            >>> print(smarter_settings.environment_platform_domain)
            'alpha.platform.example.com'
            >>> print(smarter_settings.environment_platform_domain)
            'localhost:9357'

        Note:
            Returns the root domain for the production environment. Otherwise,
            the returned domain is based on the environment and platform configuration.

        See Also:
            - smarter_settings.root_platform_domain
            - SmarterEnvironments()
            - self.environment
        """
        if self.environment == SmarterEnvironments.PROD:
            return self.root_platform_domain
        if self.environment in SmarterEnvironments.aws_environments:
            return f"{self.environment}.{self.root_platform_domain}"
        if self.environment_is_local:
            return f"localhost:{SMARTER_LOCAL_PORT}"
        # default domain format
        return f"{self.environment}.{self.root_platform_domain}"

    @cached_property
    def environment_platform_url(self) -> str:
        """
        Return the platform URL for the environment platform domain.

        Example:
            >>> print(smarter_settings.environment_platform_url)
            https://alpha.platform.example.com
            >>> print(smarter_settings.environment_platform_url)
            http://localhost:9357

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.
        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_platform_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_platform_domain: {self.environment_platform_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def all_domains(self) -> List[str]:
        """
        Return all domains for the environment.

        Domains are
        generated from the root domain, subdomains, and environments and
        are returned as a sorted list.

        Example::

            [
                'api.example.com',
                'api.alpha.platform.example.com',
                'api.beta.platform.example.com',
                'api.localhost:9357',
                'api.next.platform.example.com',
                'example.com',
                'platform.example.com',
                'alpha.platform.example.com',
                'beta.platform.example.com',
                'localhost:9357',
                'next.platform.example.com'
            ]

        See Also:
            - SmarterEnvironments()
            - smarter_settings.platform_subdomain
            - smarter_settings.api_subdomain
            - smarter_settings.platform_root_domain
            - smarter_settings.root_api_domain
            - smarter_settings.root_platform_domain
        """
        environments = [
            None,  # for root domains (no environment prefix)
            SmarterEnvironments.ALPHA,
            SmarterEnvironments.BETA,
            SmarterEnvironments.NEXT,
        ]
        subdomains = [
            self.platform_subdomain,
            self.api_subdomain,
        ]
        domains = set()
        # Add root domains
        domains.add(self.platform_root_domain)
        domains.add(self.root_api_domain)
        domains.add(self.root_platform_domain)
        # Add environment/subdomain combinations
        for subdomain in subdomains:
            # example: platform.example.com, api.platform.example.com
            domains.add(f"{subdomain}.{self.platform_root_domain}")
            for environment in environments[1:]:  # skip None for env-prefixed
                # example: alpha.platform.example.com, alpha.api.platform.example.com
                domains.add(f"{environment}.{subdomain}.{self.platform_root_domain}")
        return sorted(domains)

    @cached_property
    def environment_url(self) -> str:
        """
        Return the environment URL, derived from the environment platform domain.

        Example:
            >>> print(smarter_settings.environment_url)
            https://alpha.platform.example.com

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_platform_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_platform_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_platform_domain: {self.environment_platform_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def platform_name(self) -> str:
        """
        Return the platform name, derived from the root domain.

        Example:
            >>> print(smarter_settings.platform_name)
            'smarter'

        See Also:
            - smarter_settings.platform_root_domain
        """
        return self.platform_root_domain.split(".")[0]

    @cached_property
    def function_calling_identifier_prefix(self) -> str:
        """
        Return the prefix for function calling identifiers.

        Example:
            >>> print(smarter_settings.function_calling_identifier_prefix)
            'smarter_plugin'

        See Also:
            - smarter_settings.platform_name
        """
        return f"{self.platform_name}_plugin"

    @cached_property
    def environment_namespace(self) -> str:
        """
        Return the Kubernetes namespace for the environment.

        Example:
            >>> print(smarter_settings.environment_namespace)
            'smarter-platform-alpha'

        See Also:
            - smarter_settings.platform_subdomain
            - smarter_settings.platform_name
            - smarter_settings.environment
        """
        if self.environment_is_local:
            return f"{self.platform_name}-{SmarterEnvironments.LOCAL}"
        if self.environment in SmarterEnvironments.aws_environments:
            return f"{self.platform_name}-{self.platform_subdomain}-{self.environment}"
        raise SmarterConfigurationError(
            f"Invalid environment: {self.environment}. Please check your environment settings."
        )

    @property
    def api_subdomain(self) -> str:
        """
        Return the API subdomain for the platform.

        Example:
            >>> print(smarter_settings.api_subdomain)
            'api'
        return SMARTER_API_SUBDOMAIN
        See Also:
            - SMARTER_API_SUBDOMAIN
        """
        return SMARTER_API_SUBDOMAIN

    @cached_property
    def root_api_domain(self) -> str:
        """
        Return the root API domain name, generated from the system constant `SMARTER_API_SUBDOMAIN` and the root platform domain.

        Example:
            >>> print(smarter_settings.root_api_domain)
            'api.platform.example.com'

        See Also:
            - SMARTER_API_SUBDOMAIN
            - smarter_settings.environment_platform_domain
            - smarter_settings.api_subdomain
        """
        return f"{self.api_subdomain}.{self.platform_subdomain}.{self.platform_root_domain}"

    @cached_property
    def proxy_api_domain(self) -> str:
        """
        Return the proxy API domain name for the root domain.

        Used for proxying local requests inside of AWS Kubernetes environments
        during unit testing.

        Example:
            >>> print(smarter_settings.proxy_api_domain)
            'api.local.example.com'
        """
        return f"{self.api_subdomain}.{self.root_proxy_domain}"

    @cached_property
    def environment_api_domain(self) -> str:
        """
        Return the API domain name for the current environment.

        Example:
            >>> print(smarter_settings.environment_api_domain)
            'alpha.api.platform.example.com'
            >>> print(smarter_settings.environment_api_domain)
            'api.localhost:9357'

        Note:
            Returns the root domain for the production environment. Otherwise,
            the returned domain is based on the environment and platform configuration.
            In production, this will be the root API domain; in local or other environments,
            it will be prefixed accordingly.

        See Also:
            - smarter_settings.root_api_domain
            - smarter_settings.aws_environments
            - SmarterEnvironments()
            - SMARTER_API_SUBDOMAIN
        """
        if self.environment == SmarterEnvironments.PROD:
            return self.root_api_domain
        if self.environment in SmarterEnvironments.aws_environments:
            return f"{self.environment}.{self.root_api_domain}"
        if self.environment_is_local:
            return f"{self.api_subdomain}.localhost:{SMARTER_LOCAL_PORT}"
        # default domain format
        return f"{self.environment}.{self.root_api_domain}"

    @cached_property
    def environment_api_dns_domain(self) -> str:
        """
        Return the environment's API domain as it exists in DNS.

        In an AWS environment, it is :attr:`environment_api_domain`. Elsewhere, e.g. in local
        Docker, :attr:`environment_api_domain` is a localhost domain, which DNS cannot serve, so it
        is :attr:`proxy_api_domain`. Its DNS zone holds the A records of the LLMClients' default
        hosts, and its cert-manager ClusterIssuer, of the same name, issues their certificates.

        Example:
            >>> print(smarter_settings.environment_api_dns_domain)
            'alpha.api.platform.example.com'
            >>> print(smarter_settings.environment_api_dns_domain)
            'api.local.example.com'

        See Also:
            - smarter_settings.environment_api_domain
            - smarter_settings.proxy_api_domain
        """
        if self.environment in SmarterEnvironments.aws_environments:
            return self.environment_api_domain
        return self.proxy_api_domain

    @cached_property
    def environment_api_url(self) -> str:
        """
        Creates a valid url from smarter_settings.environment_api_domain.

        Based on the Smarter shared resource identifier and the root platform domain.
        Uses urlify() to ensure consistency in http protocol and formatting and
        trailing slash.

        Example:
            >>> print(smarter_settings.environment_api_url)
            'https://alpha.api.platform.example.com'

        Raises:
            SmarterConfigurationError: If the constructed URL is invalid.

        See Also:
            - SmarterValidator.urlify()
            - smarter_settings.environment_api_domain
            - smarter_settings.environment
        """
        retval = SmarterValidator.urlify(self.environment_api_domain, environment=self.environment)
        if retval is None:
            raise SmarterConfigurationError(
                f"Invalid environment_api_domain: {self.environment_api_domain}. "
                "Please check your environment settings."
            )
        return retval

    @cached_property
    def aws_s3_bucket_name(self) -> str:
        """
        Returns the AWS S3 bucket name for the current environment.

        The bucket name is constructed from the Smarter shared resource identifier
        and the root platform domain.

        Example:
            >>> print(smarter_settings.aws_s3_bucket_name)
            'alpha.platform.example.com'

        Note:
            In local environments, this returns 'alpha.platform.example.com' as a proxy.

        See Also:
            - smarter_settings.platform_shared_resource_identifier
            - smarter_settings.root_platform_domain
            - SmarterEnvironments()
            - smarter_settings.environment_platform_domain
        """
        if self.environment_is_local:
            return self.root_proxy_domain
        return self.environment_platform_domain

    @cached_property
    def aws_s3_exports_bucket_name(self) -> str:
        """
        Returns the name of the environment's private AWS S3 bucket for users' data exports.

        The environment's bucket, :attr:`aws_s3_bucket_name`, is public: it serves the web console and
        the chat widget through the CDN. A user's data export is private, so it goes to this bucket,
        which smarter-infrastructure creates beside it, and is downloaded with a presigned url.

        Example:
            >>> print(smarter_settings.aws_s3_exports_bucket_name)
            'exports.alpha.platform.example.com'

        See Also:
            - smarter_settings.aws_s3_bucket_name
            - smarter.apps.infrastructure.providers.aws.storage.S3StorageService
        """
        return f"exports.{self.aws_s3_bucket_name}"


__all__ = ["DomainSettings"]
