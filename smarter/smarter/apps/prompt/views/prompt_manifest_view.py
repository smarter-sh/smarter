# pylint: disable=W0613,C0302
"""
Views for the React chat component used in the Smarter web application.
"""

import logging
from typing import Optional

import yaml
from django.http import (
    HttpRequest,
    HttpResponse,
)
from django.shortcuts import render

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotHelper,
)
from smarter.apps.docs.views.base import DocsBaseView
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
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


class PromptManifestView(DocsBaseView):
    """
    Renders the detail view for a Smarter chatbot.

    This view renders a detailed manifest for a specific chatbot, including
    its configuration and metadata, in YAML format. It is intended for
    authenticated users and provides error handling for missing or
    unsupported chatbot kinds and names.

    :param request: Django HTTP request object.
    :type request: WSGIRequest
    :param args: Additional positional arguments.
    :type args: tuple
    :param kwargs: Keyword arguments, must include 'name' (chatbot name) and 'kind' (chatbot type).
    :type kwargs: dict

    :returns: Rendered HTML page with chatbot manifest details, or a 404 error page if the chatbot is not found or parameters are invalid.
    :rtype: HttpResponse

    .. note::

        The chatbot name and kind must be provided and valid. Otherwise, a "not found" response is returned.

    .. seealso::

        :class:`ChatBot` for chatbot retrieval.
        :class:`ApiV1CliDescribeApiView` for API details.

    **Example usage**::

        GET /chatbot/detail/?name=my_chatbot&kind=custom

    """

    template_path = "prompt/manifest-detail.html"

    chatbot: Optional[ChatBot] = None
    chatbot_helper: Optional[ChatBotHelper] = None

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle GET requests to render the chatbot manifest detail view.
        This method processes the incoming request to retrieve the
        specified chatbot's manifest details and renders them in a
        user-friendly format. It performs validation on the provided chatbot
        name and kind, retrieves the chatbot metadata, and handles any
        errors that may arise during this process.

        Process:
        1. Extract and validate 'name' and 'kind' from kwargs.
        2. Retrieve the chatbot metadata using the provided name and user context.
        3. If the chatbot is found, call the API view to get the chatbot details
        4. Convert the JSON response to YAML format for better readability.
        5. Render the chatbot manifest detail template with the retrieved data.
        6. Handle any errors that occur during the process and return appropriate error responses.

        :param request: Django HTTP request object.
        :type request: WSGIRequest
        :param args: Additional positional arguments.
        :type args: tuple
        :param kwargs: Keyword arguments, must include 'name' (chatbot name) and 'kind' (chatbot type).
        :type kwargs: dict

        :returns: Rendered HTML page with chatbot manifest details, or an error response if the chatbot is not found or parameters are invalid.
        :rtype: HttpResponse
        """
        logger.debug(
            "%s.dispatch() called with request=%s, args=%s, kwargs=%s",
            self.formatted_class_name,
            request.build_absolute_uri(),
            args,
            kwargs,
        )

        hashed_id = kwargs.pop("hashed_id", None)
        chatbot_id = ChatBot.id_from_hashed_id(hashed_id) if hashed_id else None
        try:
            self.chatbot = ChatBot.get_cached_object(pk=chatbot_id)

            if not isinstance(self.chatbot, ChatBot):
                raise ChatBot.DoesNotExist(
                    f"ChatBot with id {chatbot_id} does not exist. Received {type(self.chatbot)} {self.chatbot}"
                )
            self.chatbot_helper = ChatBotHelper(request=request, chatbot=self.chatbot)

            # we'll pass the chatbot name as a kwarge to the APICli
            # along with ownership info which we'll set below.
            kwargs["name"] = self.chatbot.name

            # there are many ways that we could do this, but using the system
            # const is easiest.
            self.kind = SAMKinds.CHATBOT
        except ChatBot.DoesNotExist:
            return SmarterHttpResponseNotFound(request=request, error_message=f"ChatBot with id {chatbot_id} not found")

        logger.debug(
            "%s.dispatch() - url=%s, account=%s, user=%s, chatbot=%s",
            self.formatted_class_name,
            self.url,
            self.account,
            self.user_profile.user,  # type: ignore
            self.chatbot,
        )

        # we need to re-orchestrate the parameters that we'll send to
        # self.get_brokered_json_response(), which marshals the request
        # and kwargs to the ApiV1CliDescribeApiView view to get
        # the json manifest for the chatbot. Since the chatbot has ownership
        # that is not necessarily the same as the authenticated user, we need
        # to spoof the request user to be the owner of the chatbot for the
        # purposes of generating the manifest.
        #
        # things we know:
        # - request.user was validated in the base classes.
        # - self.chatbot.user_profile was validated in ChatBotHelper
        # - user_profile always has a valid user.
        request.user = self.chatbot.user_profile.user

        logger.debug(
            "%s.dispatch() - rendering template %s with kwargs: %s",
            self.formatted_class_name,
            self.template_path,
            kwargs,
        )

        # to avoid circular imports at app startup.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
        from smarter.apps.api.v1.cli.views.describe import ApiV1CliDescribeApiView

        # build the relative url path to the API CLI end point.
        reverse_name = str(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.describe).lower()
        view = ApiV1CliDescribeApiView.as_view()
        json_response = self.get_brokered_json_response(
            reverse_name=reverse_name,
            view=view,
            request=request,
            *args,
            **kwargs,
        )

        try:
            yaml_response = yaml.dump(json_response, default_flow_style=False)
        except yaml.YAMLError as e:
            logger.error(
                "%s.dispatch() - Error converting JSON response to YAML: %s. JSON response: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(json_response),
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error converting manifest to YAML")

        context = {
            "manifest": yaml_response,
            "page_title": self.chatbot.name,
            "owner": self.chatbot.user_profile,
        }
        try:
            response = render(request, self.template_path, context=context)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.dispatch() - Error rendering template: %s. context: %s",
                self.formatted_class_name,
                str(e),
                formatted_json(context),
                exec_info=True,
            )
            return SmarterHttpResponseServerError(request=request, error_message="Error rendering manifest page")
        return response
