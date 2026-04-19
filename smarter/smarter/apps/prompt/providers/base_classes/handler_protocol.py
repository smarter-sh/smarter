# pylint: disable=C0302
"""
Base class for chat providers.
"""

import logging
from typing import Any, List, Optional, Protocol, Union

from smarter.apps.account.models import User
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.prompt.models import Chat

# smarter chat provider stuff
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

# 3rd party stuff


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class HandlerProtocol(Protocol):
    """
    A fixed Protocol for all chat provider handler functions.
    Ensures that all handler functions have exactly the same signature.

    :param user: The user making the request.
    :type user: User
    :param chat: The chat object.
    :type chat: Chat
    :param data: The request data.
    :type data: Union[dict[str, Any], list]
    :param plugins: Optional list of plugins to use.
    :type plugins: Optional[List[PluginBase]]
    :param functions: Optional list of function names to use.
    :type functions: Optional[list[str]]

    :returns: The response data.
    :rtype: Union[dict[str, Any], list]
    """

    def __call__(
        self,
        user: User,
        chat: Chat,
        data: Union[dict[str, Any], list],
        plugins: Optional[List[PluginBase]] = None,
        functions: Optional[list[str]] = None,
    ) -> Union[dict[str, Any], list]: ...


__all__ = ["HandlerProtocol"]
