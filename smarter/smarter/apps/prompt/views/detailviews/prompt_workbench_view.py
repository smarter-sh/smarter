# pylint: disable=W0613,C0302
"""
The Prompt Engineer's Workbench's page, :class:`PromptWorkbenchView`, and the chat's prompt session.

:class:`SmarterPromptSession` is the chat session of a prompt, which the chat's configuration api,
:class:`~smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView`, creates or resumes.
"""

from typing import Optional

from django.http import (
    HttpRequest,
)

from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.apps.llmclient.models import (
    LLMClient,
)
from smarter.apps.prompt.models import Prompt, PromptHelper
from smarter.apps.prompt.signals import prompt_session_invoked
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import (
    SmarterException,
)
from smarter.common.helpers.url_helpers import clean_url
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

MAX_RETURNED_PLUGINS = 10
PROMPT_LIST_CACHE_TIMEOUT = smarter_settings.cache_expiration
WORKBENCH_CACHE_TIMEOUT = 10  # 10 seconds. keeps the workbench snappy while avoiding appearing stale.


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


def should_log_verbose(level):
    """Check if logging should be done based on the waffle switch."""
    return smarter_settings.verbose_logging


verbose_logger = WaffleSwitchedLoggerWrapper(base_logger, should_log_verbose)


class SmarterChatappViewError(SmarterException):
    """Base class for all SmarterChatapp errors."""

    @property
    def get_formatted_err_message(self):
        """The fixed error message prefix of the chatapp views."""
        return "Smarter Chatapp error"


class SmarterPromptSession(SmarterHelperMixin):
    """Helper class that provides methods for creating a session key and client key."""

    _chat: Optional[Prompt] = None
    _chat_helper: Optional[PromptHelper] = None
    _llmclient: Optional[LLMClient] = None
    request: Optional[HttpRequest] = None
    _session_key: str

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{SmarterPromptSession.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def __init__(self, request: HttpRequest, session_key: str, *args, llmclient: Optional[LLMClient] = None, **kwargs):
        super().__init__()
        verbose_logger.debug(
            "SmarterPromptSession().__init__() called with session_key=%s, llmclient=%s", session_key, llmclient
        )
        self.request = request
        if not isinstance(session_key, str):
            logger.error("%s session_key is not a string: %s", self.formatted_class_name, type(session_key))
        self._session_key = session_key

        if llmclient:
            self._llmclient = llmclient
            self.user_profile = llmclient.user_profile

        # leaving this in place as a reminder that we need one or the other
        if not self.session_key and not self.llmclient:
            logger.error("%s either session_key or llmclient must be provided", self.formatted_class_name)

        self._chat_helper = PromptHelper(request, self.session_key, *args, llmclient=self.llmclient, **kwargs)
        self._chat = self._chat_helper.prompt
        # PromptHelper starts a new session when the key belongs to another llmclient's session.
        self._session_key = self._chat_helper.session_key

        verbose_logger.debug("%s session established: %s", self.formatted_class_name, self.session_key)

        prompt_session_invoked.send(sender=self.__class__, instance=self, request=request)

    def __str__(self) -> str:
        """
        Returns a string representation of the session, naming its concrete class.

        :return: String representation of the session.
        :rtype: str
        """
        return f"{self.__class__.__name__}[{id(self)}](llmclient={self.llmclient}, session_key={self.session_key})"

    def __repr__(self) -> str:
        """
        Returns the developer representation of the session, which is the same as :meth:`__str__`.

        :return: Developer representation of the session.
        :rtype: str
        """
        return self.__str__()

    def __hash__(self) -> int:
        """
        Returns the hash of the session key, consistent with :meth:`__eq__`.

        :return: Hash of the session key.
        :rtype: int
        """
        return hash(self.session_key)

    def __eq__(self, other: object) -> bool:
        """
        Two sessions are equal when they have the same session key.

        :param other: The object to compare to.
        :type other: object
        :return: True if the session keys are equal, or ``NotImplemented`` if
            ``other`` is not a :class:`SmarterPromptSession`.
        :rtype: bool
        """
        if not isinstance(other, SmarterPromptSession):
            return NotImplemented
        return self.session_key == other.session_key

    @property
    def session_key(self) -> str:
        """
        The session key for this prompt session.

        This is used to identify the prompt session
        and is generated by the /config/ endpoint.
        """
        if self._session_key is None:
            logger.error(
                "%s session_key is None. This should not happen. Please report this issue to the Smarter team.",
                self.formatted_class_name,
            )
        return self._session_key

    @property
    def llmclient(self):
        """The LLMClient of the session."""
        return self._llmclient

    @property
    def prompt(self):
        """The Prompt of the session."""
        return self._chat

    @property
    def chat_helper(self):
        """The PromptHelper of the session."""
        return self._chat_helper

    def clean_url(self, url: str) -> str:
        """Clean the url of any query strings and trailing '/config/' strings."""
        retval = clean_url(url)
        if retval.endswith("/config/"):
            retval = retval[:-8]
        return retval


class PromptWorkbenchView(ConsoleAppView):
    """
    The Prompt Engineer's Workbench of an LLMClient, ``/workbench/llm-clients/<hashed_id>/prompt/``: the single-page.

    console's page (ADR-035).

    The console renders ``@smarter/workbench``, the chat with the LLMClient, Smarter Chat (the ``@smarter.sh/ui-chat``
    npm package), and the developer Console beside it, configured from the hashed id and the console's session: the
    chat reads its configuration from the public api, ``/api/v1/llm-clients/<hashed_id>/config/``
    (:class:`~smarter.apps.prompt.views.detailviews.prompt_config_view.PromptConfigView`), and the Console's tabs
    call the web console's api, ``/api/web/prompt/llm-clients/<hashed_id>/``. The console first asks the resource
    api for the LLMClient, and shows Page not found to a user who may not read it. Django keeps this view at the
    path it served the page at, so that its url name, and ``LLMClient.workbench_url``, still reverse.
    """
