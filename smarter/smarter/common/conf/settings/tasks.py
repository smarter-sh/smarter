# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The settings of the Celery tasks that deploy LLMClients and manage infrastructure."""

from typing import Optional, Union

from pydantic import BaseModel, Field

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.defaults import settings_defaults
from smarter.common.conf.util import before_field_validator, parse_int_setting
from smarter.common.exceptions import SmarterConfigurationError


class TaskSettings(BaseModel):
    """The Celery queues, retries and LLMClient deployment tasks."""

    app_llmclient_tasks_create_dns_record: bool = Field(
        settings_defaults.APP_LLMCLIENT_TASKS_CREATE_DNS_RECORD,
        description="True if DNS records should be created for llmclient tasks.",
        title="LLMClient Tasks Create DNS Record",
    )
    """
    Set these to true if we *DO NOT* place a wildcard A record in the customer API domain.

    requiring that every llmclient have its own A record. This is the default behavior.
    For programmatically creating DNS records in AWS Route53 during LLMClient deployment.

    :type: bool
    :default: Value from ``settings_defaults.APP_LLMCLIENT_TASKS_CREATE_DNS_RECORD``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("app_llmclient_tasks_create_dns_record")
    def parse_app_llmclient_tasks_create_dns_record(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'llmclient_tasks_create_dns_record' field.

        Args:
            v (Optional[Union[bool, str]]): the llmclient_tasks_create_dns_record value to validate

        Returns:
            bool: The validated llmclient_tasks_create_dns_record.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.APP_LLMCLIENT_TASKS_CREATE_DNS_RECORD
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate llmclient_tasks_create_dns_record: {v}")

    app_llmclient_tasks_create_ingress_manifest: bool = Field(
        settings_defaults.APP_LLMCLIENT_TASKS_CREATE_INGRESS_MANIFEST,
        description="True if ingress manifests should be created for llmclient tasks.",
        title="LLMClient Tasks Create Ingress Manifest",
    )
    """
    True if ingress manifests should be created for llmclient tasks.

    For programmatically creating ingress manifests during LLMClient deployment.
    :type: bool
    :default: Value from ``settings_defaults.APP_LLMCLIENT_TASKS_CREATE_INGRESS_MANIFEST``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("app_llmclient_tasks_create_ingress_manifest")
    def parse_app_llmclient_tasks_create_ingress_manifest(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'llmclient_tasks_create_ingress_manifest' field.

        Args:
            v (Optional[Union[bool, str]]): the llmclient_tasks_create_ingress_manifest value to validate
        Returns:
            bool: The validated llmclient_tasks_create_ingress_manifest.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.APP_LLMCLIENT_TASKS_CREATE_INGRESS_MANIFEST
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate llmclient_tasks_create_ingress_manifest: {v}")

    app_llmclient_tasks_default_ttl: int = Field(
        settings_defaults.APP_LLMCLIENT_TASKS_DEFAULT_TTL,
        description="Default TTL (time to live) for DNS records created in AWS Route53 during LLMClient deployment.",
        title="LLMClient Tasks Default TTL",
        ge=0,
    )
    """
    Default TTL (time to live) for DNS records created in AWS Route53 during LLMClient deployment.

    :type: int
    :default: Value from ``settings_defaults.APP_LLMCLIENT_TASKS_DEFAULT_TTL``
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("app_llmclient_tasks_default_ttl")
    def parse_app_llmclient_tasks_default_ttl(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'llmclient_tasks_default_ttl' field.

        Args:
            v (Optional[Union[int, str]]): the llmclient_tasks_default_ttl value to validate
        Returns:
            int: The validated llmclient_tasks_default_ttl.
        """
        return parse_int_setting(
            "app_llmclient_tasks_default_ttl", v, settings_defaults.APP_LLMCLIENT_TASKS_DEFAULT_TTL, minimum=0
        )

    app_llmclient_tasks_celery_max_retries: int = Field(
        settings_defaults.APP_LLMCLIENT_TASKS_CELERY_MAX_RETRIES,
        gt=0,
        description="Maximum number of retries for llmclient tasks in Celery.",
        title="LLMClient Tasks Celery Max Retries",
    )
    """
    Maximum number of retries for llmclient tasks in Celery.

    :type: int
    :default: Value from ``settings_defaults.APP_LLMCLIENT_TASKS_CELERY_MAX_RETRIES``
    :raises SmarterConfigurationError: If the value is not a non-negative integer.
    """

    @before_field_validator("app_llmclient_tasks_celery_max_retries")
    def parse_app_llmclient_tasks_celery_max_retries(cls, v: Optional[Union[int, str]]) -> int:
        """Validates the 'llmclient_tasks_celery_max_retries' field.

        Args:
            v (Optional[Union[int, str]]): the llmclient_tasks_celery_max_retries value to validate
        Returns:
            int: The validated llmclient_tasks_celery_max_retries.
        """
        return parse_int_setting(
            "app_llmclient_tasks_celery_max_retries", v, settings_defaults.APP_LLMCLIENT_TASKS_CELERY_MAX_RETRIES
        )

    app_llmclient_tasks_celery_retry_backoff: bool = Field(
        settings_defaults.APP_LLMCLIENT_TASKS_CELERY_RETRY_BACKOFF,
        description="If True, enables exponential backoff for Celery task retries related to LLMClient deployment and management",
        title="LLMClient Tasks Celery Retry Backoff",
    )
    """
    If True, enables exponential backoff for Celery task retries related to LLMClient deployment and management.

    :type: bool
    :default: Value from ``settings_defaults.APP_LLMCLIENT_TASKS_CELERY_RETRY_BACKOFF``
    :raises SmarterConfigurationError: If the value is not a boolean.
    """

    @before_field_validator("app_llmclient_tasks_celery_retry_backoff")
    def parse_app_llmclient_tasks_celery_retry_backoff(cls, v: Optional[Union[bool, str]]) -> bool:
        """Validates the 'llmclient_tasks_celery_retry_backoff' field.

        Args:
            v (Optional[Union[bool, str]]): the llmclient_tasks_celery_retry_backoff value to validate
        Returns:
            bool: The validated llmclient_tasks_celery_retry_backoff.
        """
        if isinstance(v, bool):
            return v
        if v in THE_EMPTY_SET:
            return settings_defaults.APP_LLMCLIENT_TASKS_CELERY_RETRY_BACKOFF
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate llmclient_tasks_celery_retry_backoff: {v}")

    app_llmclient_tasks_celery_task_queue: str = Field(
        settings_defaults.APP_LLMCLIENT_TASKS_CELERY_TASK_QUEUE,
        description="The Celery task queue name for llmclient tasks.",
        title="LLMClient Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for llmclient tasks.

    :type: str
    :default: Value from ``settings_defaults.APP_LLMCLIENT_TASKS_CELERY_TASK_QUEUE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("app_llmclient_tasks_celery_task_queue")
    def validate_app_llmclient_tasks_celery_task_queue(cls, v: Optional[str]) -> str:
        """Validates the `llmclient_tasks_celery_task_queue` field.

        Args:
            v (Optional[str]): The llmclient tasks celery task queue value to validate.
        Returns:
            str: The validated llmclient tasks celery task queue.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.APP_LLMCLIENT_TASKS_CELERY_TASK_QUEUE

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llmclient_tasks_celery_task_queue of type {type(v)} is not a str: {v}")

        return v

    app_infrastructure_tasks_celery_task_queue: str = Field(
        settings_defaults.APP_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE,
        description="The Celery task queue name for infrastructure tasks, which deploy, verify and destroy cloud, Kubernetes and DNS resources.",
        title="Infrastructure Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for infrastructure tasks.

    Infrastructure tasks deploy, verify and destroy cloud, Kubernetes and DNS resources, such as
    an LLMClient's DNS record, ingress and certificate, an LLMHost's node group, or a vectorstore's
    database. They can take many minutes, so they run in their own queue, served by their own
    Celery worker, and never block the operational tasks of llmclient_tasks_celery_task_queue,
    such as prompt history, charges and budgets.

    :type: str
    :default: Value from ``settings_defaults.APP_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("app_infrastructure_tasks_celery_task_queue")
    def validate_app_infrastructure_tasks_celery_task_queue(cls, v: Optional[str]) -> str:
        """Validates the `infrastructure_tasks_celery_task_queue` field.

        Args:
            v (Optional[str]): The llmclient tasks celery task queue value to validate.
        Returns:
            str: The validated llmclient tasks celery task queue.
        """
        if v in THE_EMPTY_SET:
            return settings_defaults.APP_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE

        if not isinstance(v, str):
            raise SmarterConfigurationError(
                f"infrastructure_tasks_celery_task_queue of type {type(v)} is not a str: {v}"
            )

        return v


__all__ = ["TaskSettings"]
