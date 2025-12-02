# pylint: disable=W0613
"""
Smarter API command-line interface Brokers. These are the broker classes
that implement the broker service pattern for an underlying object. Brokers
receive a Yaml manifest representation of a model, convert this to a Pydantic
model, and then instantiate the appropriate Python class that performs
the necessary operations to facilitate cli requests that include:
    - delete
    - deploy
    - describe
    - get
    - logs
    - manifest
    - undeploy
"""

import logging
from typing import Dict, Optional, Type
from urllib.parse import urlparse

from smarter.apps.account.manifest.brokers.account import SAMAccountBroker
from smarter.apps.account.manifest.brokers.secret import SAMSecretBroker
from smarter.apps.account.manifest.brokers.user import SAMUserBroker
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.plugin.manifest.brokers.api_connection import SAMApiConnectionBroker
from smarter.apps.plugin.manifest.brokers.api_plugin import SAMApiPluginBroker
from smarter.apps.plugin.manifest.brokers.sql_connection import SAMSqlConnectionBroker
from smarter.apps.plugin.manifest.brokers.sql_plugin import SAMSqlPluginBroker
from smarter.apps.plugin.manifest.brokers.static_plugin import SAMStaticPluginBroker
from smarter.apps.prompt.manifest.brokers.chat import SAMChatBroker
from smarter.apps.prompt.manifest.brokers.chat_history import SAMChatHistoryBroker
from smarter.apps.prompt.manifest.brokers.chat_plugin_usage import (
    SAMChatPluginUsageBroker,
)
from smarter.apps.prompt.manifest.brokers.chat_tool_call import SAMChatToolCallBroker
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthTokenBroker
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker  # BrokerNotImplemented


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class Brokers:
    """
    The Broker service pattern for the Smarter Broker Model.

    This class provides the mapping and logic for selecting the correct Broker
    implementation based on the manifest ``Kind``. Brokers are used throughout
    the ``api/v1/cli`` interface to process Smarter YAML manifests and to
    facilitate common CLI operations, including:

        - ``apply``
        - ``delete``
        - ``deploy``
        - ``describe``
        - ``get``
        - ``manifest``
        - ``example``
        - ``status``
        - ``undeploy``
        - ``logs``
        - ``schema``

    Each Broker is responsible for brokering the correct implementation class
    for a given operation by analyzing the manifest's ``Kind`` field. This
    enables a unified interface for handling different resource types in the
    Smarter platform.

    Key Methods
    -----------
    get_broker(kind: str) -> Optional[Type[AbstractBroker]]:
        Returns the Broker class definition for the given manifest kind.
        The lookup is case-insensitive.

    Usage
    -----
    Brokers are primarily used for processing Smarter YAML manifests in CLI
    workflows. By calling :meth:`get_broker`, you can retrieve the appropriate
    Broker class to handle a specific resource type.

    Example
    -------
    >>> broker_cls = Brokers.get_broker("Account")
    >>> broker = broker_cls()
    >>> broker.describe(...)

    """

    _brokers: Dict[str, Type[AbstractBroker]] = {
        SAMKinds.ACCOUNT.value: SAMAccountBroker,
        SAMKinds.AUTH_TOKEN.value: SAMSmarterAuthTokenBroker,
        SAMKinds.CHAT.value: SAMChatBroker,
        SAMKinds.CHAT_HISTORY.value: SAMChatHistoryBroker,
        SAMKinds.CHAT_PLUGIN_USAGE.value: SAMChatPluginUsageBroker,
        SAMKinds.CHAT_TOOL_CALL.value: SAMChatToolCallBroker,
        SAMKinds.CHATBOT.value: SAMChatbotBroker,
        SAMKinds.STATIC_PLUGIN.value: SAMStaticPluginBroker,
        SAMKinds.API_PLUGIN.value: SAMApiPluginBroker,
        SAMKinds.SQL_PLUGIN.value: SAMSqlPluginBroker,
        SAMKinds.SQL_CONNECTION.value: SAMSqlConnectionBroker,
        SAMKinds.API_CONNECTION.value: SAMApiConnectionBroker,
        SAMKinds.USER.value: SAMUserBroker,
        SAMKinds.SECRET.value: SAMSecretBroker,
    }

    @classmethod
    def _lower_brokers(cls):
        return {k.lower(): v for k, v in cls._brokers.items()}

    @classmethod
    def get_broker(cls, kind: str) -> Optional[Type[AbstractBroker]]:
        """Case insensitive broker getter."""
        return cls._brokers.get(kind) or cls._lower_brokers().get(kind.lower())

    @classmethod
    def snake_to_camel(cls, snake_str):
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @classmethod
    def get_broker_kind(cls, kind: str) -> Optional[str]:
        """
        Case insensitive broker kind getter. Returns the original SAMKinds
        key string from cls._brokers for the given kind.
        """
        if not kind:
            return None

        # remove trailing 's' from kind if it exists
        if kind.endswith("s"):
            kind = kind[:-1]

        # ensure kind is in camel case
        kind = cls.snake_to_camel(kind)
        lower_kind = kind.lower()

        # perform a lower case search to find and return the original key
        # in the cls._brokers dictionary
        for key in cls._brokers:
            if key.lower() == lower_kind:
                return key
        return None

    @classmethod
    def all_brokers(cls) -> list[str]:
        return list(cls._brokers.keys())

    @classmethod
    def from_url(cls, url) -> Optional[str]:
        """
        Returns the kind of broker from the given URL. This is used to
        determine the broker to use when the kind is not provided in the
        request.

        example: http://localhost:8000/api/v1/cli/example_manifest/account/
        returns: "Account"
        """
        parsed_url = urlparse(url)
        if parsed_url:
            slugs = parsed_url.path.split("/")
            if not "api" in slugs:
                return None
            for slug in slugs:
                this_slug = str(slug).lower()
                kind = cls.get_broker_kind(this_slug)
                if kind:
                    return kind
        logger.warning("Brokers.from_url() could not extract manifest kind from URL: %s", url)


# an internal self-check to ensure that all SAMKinds have a Broker implementation
if not all(item in SAMKinds.all_values() for item in Brokers.all_brokers()):
    brokers_keys = set(Brokers.all_brokers())
    samkinds_values = set(SAMKinds.all_values())
    difference = brokers_keys.difference(samkinds_values)
    difference_list = list(difference)
    if len(difference_list) == 1:
        difference_list = difference_list[0]
    raise SmarterConfigurationError(
        f"The following broker(s) is missing from the master BROKERS dictionary: {difference_list}"
    )
