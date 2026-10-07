# pylint: disable=W0613
"""
API view for the Dashboard "Getting Started" React component.

Returns the onboarding steps of a new user, each with whether the user has
done it and a link to the console page where it is done. The React component
hides itself once every step is done.
"""

from http import HTTPStatus

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import UserProfile, get_resolved_user
from smarter.apps.dashboard.views.views.api.my_resources import (
    get_llmclients,
    get_plugins,
    get_secrets,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.plugin.urls import PluginReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.secret.urls import SecretReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedWebView
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.urls import AuthTokenReverseNames


class GettingStartedView(SmarterAuthenticatedWebView):
    """
    The onboarding steps of the user, and whether each is done.

    The API key step is only for staff users, who are the only users that may
    create API keys.

    Response shape:

    .. code-block:: json

        {
            "steps": [
                {
                    "name": "Store a Secret",
                    "description": "Keep LLM provider and connection credentials encrypted.",
                    "done": true,
                    "url": "/secret/"
                }
            ]
        }
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        user = get_resolved_user(request.user)
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
        steps = []
        if getattr(user, "is_staff", False):
            steps.append(
                {
                    "name": "Create an API key",
                    "description": "Authenticate the Smarter CLI and the REST API.",
                    "done": SmarterAuthToken.objects.filter(user=user).exists(),
                    "url": reverse(AuthTokenReverseNames.namespace, AuthTokenReverseNames.listview),
                }
            )
        steps += [
            {
                "name": "Store a Secret",
                "description": "Keep LLM provider and connection credentials encrypted.",
                "done": get_secrets(user_profile=user_profile) > 0,
                "url": reverse(SecretReverseNames.namespace, SecretReverseNames.listview),
            },
            {
                "name": "Create an LLM Client",
                "description": "Configure an LLM, its system prompt and its tools.",
                "done": get_llmclients(user_profile=user_profile) > 0,
                "url": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
            },
            {
                "name": "Add a Plugin",
                "description": "Give your LLM Client data and tools to work with.",
                "done": get_plugins(user_profile=user_profile) > 0,
                "url": reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
            },
            {
                "name": "Deploy an LLM Client",
                "description": "Publish it to its own URL for your users and applications.",
                "done": LLMClient.objects.filter(user_profile=user_profile, deployed=True).exists(),
                "url": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
            },
        ]
        return JsonResponse({"steps": steps}, status=HTTPStatus.OK)
