# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""The settings of the Celery tasks that deploy LLMClients and manage infrastructure."""

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from smarter.common.conf.const import THE_EMPTY_SET
from smarter.common.conf.util import (
    before_field_validator,
    field_default,
    parse_int_setting,
)
from smarter.common.exceptions import SmarterConfigurationError


class TaskSettings(BaseModel):
    """The Celery queues, retries and LLMClient deployment tasks."""

    app_llmclient_tasks_create_dns_record: bool = Field(
        True,
        description="True if DNS records should be created for llmclient tasks.",
        title="LLMClient Tasks Create DNS Record",
    )
    """
    Set these to true if we *DO NOT* place a wildcard A record in the customer API domain.

    requiring that every llmclient have its own A record. This is the default behavior.
    For programmatically creating DNS records in AWS Route53 during LLMClient deployment.

    :type: bool
    :default: ``True``
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
            return field_default(cls, "app_llmclient_tasks_create_dns_record")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate llmclient_tasks_create_dns_record: {v}")

    app_llmclient_tasks_create_ingress_manifest: bool = Field(
        True,
        description="True if ingress manifests should be created for llmclient tasks.",
        title="LLMClient Tasks Create Ingress Manifest",
    )
    """
    True if ingress manifests should be created for llmclient tasks.

    For programmatically creating ingress manifests during LLMClient deployment.
    :type: bool
    :default: ``True``
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
            return field_default(cls, "app_llmclient_tasks_create_ingress_manifest")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate llmclient_tasks_create_ingress_manifest: {v}")

    app_llmclient_tasks_default_ttl: int = Field(
        600,
        description="Default TTL (time to live) for DNS records created in AWS Route53 during LLMClient deployment.",
        title="LLMClient Tasks Default TTL",
        ge=0,
    )
    """
    Default TTL (time to live) for DNS records created in AWS Route53 during LLMClient deployment.

    :type: int
    :default: ``600``
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
            "app_llmclient_tasks_default_ttl", v, field_default(cls, "app_llmclient_tasks_default_ttl"), minimum=0
        )

    app_llmclient_tasks_celery_max_retries: int = Field(
        3,
        gt=0,
        description="Maximum number of retries for llmclient tasks in Celery.",
        title="LLMClient Tasks Celery Max Retries",
    )
    """
    Maximum number of retries for llmclient tasks in Celery.

    :type: int
    :default: ``3``
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
            "app_llmclient_tasks_celery_max_retries", v, field_default(cls, "app_llmclient_tasks_celery_max_retries")
        )

    app_llmclient_tasks_celery_retry_backoff: bool = Field(
        True,
        description="If True, enables exponential backoff for Celery task retries related to LLMClient deployment and management",
        title="LLMClient Tasks Celery Retry Backoff",
    )
    """
    If True, enables exponential backoff for Celery task retries related to LLMClient deployment and management.

    :type: bool
    :default: ``True``
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
            return field_default(cls, "app_llmclient_tasks_celery_retry_backoff")
        if isinstance(v, str):
            return v.lower() in ["true", "1", "t", "y", "yes"]

        raise SmarterConfigurationError(f"could not validate llmclient_tasks_celery_retry_backoff: {v}")

    app_llmclient_tasks_celery_task_queue: str = Field(
        "default_celery_task_queue",
        description="The Celery task queue name for llmclient tasks.",
        title="LLMClient Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for llmclient tasks.

    :type: str
    :default: ``"default_celery_task_queue"``
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
            return field_default(cls, "app_llmclient_tasks_celery_task_queue")

        if not isinstance(v, str):
            raise SmarterConfigurationError(f"llmclient_tasks_celery_task_queue of type {type(v)} is not a str: {v}")

        return v

    app_infrastructure_tasks_celery_task_queue: str = Field(
        "infrastructure_celery_task_queue",
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
    :default: ``"infrastructure_celery_task_queue"``
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
            return field_default(cls, "app_infrastructure_tasks_celery_task_queue")

        if not isinstance(v, str):
            raise SmarterConfigurationError(
                f"infrastructure_tasks_celery_task_queue of type {type(v)} is not a str: {v}"
            )

        return v

    app_tools_tasks_celery_task_queue: str = Field(
        "tools_celery_task_queue",
        description="The Celery task queue name for LLM tool calls, which the tool worker, smarter-worker-tools, runs.",
        title="Tools Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for LLM tool calls, when ``app_llmtool_tool_runner`` is ``remote``.

    The tool worker, ``smarter-worker-tools``, serves it: it runs each tool call without the database or
    the platform's credentials (ADR-038). See :mod:`smarter.apps.llmtool.runner`.

    :type: str
    :default: ``"tools_celery_task_queue"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("app_tools_tasks_celery_task_queue")
    def validate_app_tools_tasks_celery_task_queue(cls, v: Optional[str]) -> str:
        """
        Validate ``app_tools_tasks_celery_task_queue``.

        :param v: The queue's name, or empty for the default.
        :returns: The queue's name.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "app_tools_tasks_celery_task_queue")
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"app_tools_tasks_celery_task_queue of type {type(v)} is not a str: {v}")
        return v

    app_extensions_tasks_celery_task_queue: str = Field(
        "extensions_celery_task_queue",
        description="The Celery task queue name for Extensions' tool calls, which smarter-worker-extensions runs.",
        title="Extensions Tasks Celery Task Queue",
    )
    """
    The Celery task queue name for Extensions' tool calls, when ``app_llmtool_tool_runner`` is ``remote``.

    The Extension worker, ``smarter-worker-extensions``, serves it, apart from the tool worker, which runs every
    other kind of tool call (issue #1077). An Extension is third-party code: in a worker of its own, each call in
    a process of its own, and with a Redis user that reaches only this queue, it can't see the API, SQL and MCP
    calls' credentials, neither in its process nor waiting in Redis. Its name doesn't start with
    ``app_tools_tasks_celery_task_queue``'s, so that the tool worker's Redis user, whose keys are that queue's
    prefix, can't read it either.

    :type: str
    :default: ``"extensions_celery_task_queue"``
    :raises SmarterConfigurationError: If the value is not a string.
    """

    @before_field_validator("app_extensions_tasks_celery_task_queue")
    def validate_app_extensions_tasks_celery_task_queue(cls, v: Optional[str]) -> str:
        """
        Validate ``app_extensions_tasks_celery_task_queue``.

        :param v: The queue's name, or empty for the default.
        :returns: The queue's name.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET:
            return field_default(cls, "app_extensions_tasks_celery_task_queue")
        if not isinstance(v, str):
            raise SmarterConfigurationError(
                f"app_extensions_tasks_celery_task_queue of type {type(v)} is not a str: {v}"
            )
        return v

    app_tools_worker_queue: Optional[str] = Field(
        None,
        description=(
            "The queue that this tool worker consumes: the tools or the Extensions queue. Empty in every other "
            "process."
        ),
        title="Tool Worker Queue",
    )
    """
    The queue that this tool worker consumes, set in the tool worker and in the Extension worker only.

    Both are workers without a database (``database_unavailable``), and they differ only by their queue. Each
    keeps kombu's in-flight messages under its queue's name (``CELERY_BROKER_TRANSPORT_OPTIONS``), checks that
    its Redis user reaches that queue and no other, runs only that queue's kind of tool call, and names it in
    the line that ends its startup checks. Empty, a worker without a database is the tool worker. See
    :attr:`tool_worker_queue`.

    Set it with ``SMARTER_APP_TOOLS_WORKER_QUEUE``.

    :type: Optional[str]
    :default: None
    """

    @before_field_validator("app_tools_worker_queue")
    def validate_app_tools_worker_queue(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate ``app_tools_worker_queue``.

        :param v: The queue's name, or empty.
        :returns: The queue's name, or None.
        :raises SmarterConfigurationError: If the value is not a string.
        """
        if v in THE_EMPTY_SET:
            return None
        if not isinstance(v, str):
            raise SmarterConfigurationError(f"app_tools_worker_queue of type {type(v)} is not a str: {v}")
        queue = v.strip()
        if not queue:
            return None
        return queue

    @property
    def tool_worker_queue(self) -> str:
        """
        The queue of this worker without a database: ``app_tools_worker_queue``, or else the tools queue.

        :returns: The queue's name.
        """
        if self.app_tools_worker_queue:
            return self.app_tools_worker_queue
        return self.app_tools_tasks_celery_task_queue

    app_llmtool_tool_runner: Literal["in_process", "remote"] = Field(
        "in_process",
        description=(
            "Where LLM tool calls run: in_process, in the app's own process, or remote, in the tool worker, "
            "smarter-worker-tools, which holds no credentials."
        ),
        title="LLM Tool Runner",
    )
    """
    Where LLM tool calls run.

    - ``in_process``, the default: in the process that handles the chat, as they always have.
    - ``remote``: in the tool worker, ``smarter-worker-tools``, through the Celery queue
      ``app_tools_tasks_celery_task_queue``. The worker holds no database, no Smarter Secret and no cloud
      credential: each call brings what it needs (ADR-038). The worker must be running.

    Set it with ``SMARTER_APP_LLMTOOL_TOOL_RUNNER``. See :mod:`smarter.apps.llmtool.runner`.

    :type: str
    :default: ``"in_process"``
    """


__all__ = ["TaskSettings"]
