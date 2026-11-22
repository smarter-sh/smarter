# pylint: disable=W0613
"""
API views for the web console's welcome dialog, the ``@smarter/welcome`` React app.

The dialog opens by itself on the first console page that a user visits after
they sign in, until they first close it, and from then on only while its first
step's **Show at startup** box is ticked, which it isn't unless the user ticks
it. It opens again whenever they choose Welcome Tour in the user menu. Closing
it, in any way, records that the user has seen it, the date in
:attr:`UserProfile.welcomed_at
<smarter.apps.account.models.UserProfile.welcomed_at>`, and the box's choice,
:attr:`UserProfile.show_welcome_at_startup
<smarter.apps.account.models.UserProfile.show_welcome_at_startup>`, on every
device. Either way, it doesn't open by itself again in the same session.

- ``welcome/`` returns the links that the dialog's last step offers. The
  dialog's text lives in the React app, where it is translated.
- ``welcome/dismiss/`` records that the user has been welcomed, and whether it
  shows at startup.
"""

from http import HTTPStatus

from cache_results import cache_results
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.common.conf import smarter_settings
from smarter.lib import json, logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedWebView

logger = logging.getSmarterLogger(__name__)

WEATHER_LLMCLIENT_NAME = "weather"
"""The example LLMClient that the welcome dialog suggests trying first.

See ``smarter/llm-clients/llmclient-weather.yaml`` in https://github.com/smarter-sh/example-manifests.
"""

WELCOME_SHOWN_SESSION_KEY = "smarter_welcome_shown"
"""The session key that is set once the user has closed the welcome dialog in this session.

The dialog opens by itself at most once per session, i.e. once each time the user signs in.
"""


class WelcomeUrls(BaseModel):
    """
    The links that the welcome dialog's last step offers.

    :param weather: The Prompt Workbench chat of the Get Weather example LLMClient, or ``None`` if the
        user can't read one, e.g. on a platform that hasn't added the examples.
    :param llmclients: The Prompt Workbench's list of the LLMClients that the user can read.
    :param docs: The documentation site, docs.smarter.sh.
    :param project: The Smarter project's website, smarter.sh.
    """

    model_config = ConfigDict(extra="forbid")

    weather: str | None
    llmclients: str
    docs: str
    project: str


class WelcomeDismissRequest(BaseModel):
    """
    The body of a request to the welcome dismiss api.

    :param show_at_startup: Whether the dialog opens by itself each time the user signs in, from now on:
        the first step's **Show at startup** box. An empty body is ``False``.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    show_at_startup: bool = Field(False, alias="showAtStartup")


class WelcomeApiResponse(BaseModel):
    """
    The response of both welcome dialog api views.

    :param welcomed: Whether the user has closed the welcome dialog before. It then opens by itself only
        while its **Show at startup** box is ticked.
    :param urls: The links that the dialog's last step offers.
    """

    model_config = ConfigDict(extra="forbid")

    welcomed: bool
    urls: WelcomeUrls


@cache_results()
def user_was_welcomed(user_id: int) -> bool:
    """
    Whether the user has closed the welcome dialog before, in any of their accounts.

    The console's session asks on every page load, so the answer is cached until
    :class:`WelcomeDismissView` invalidates it.

    :param user_id: The id of the Django user.
    :type user_id: int
    :returns: True once the user has closed the welcome dialog.
    :rtype: bool
    """
    return UserProfile.objects.filter(user_id=user_id, welcomed_at__isnull=False).exists()


@cache_results()
def user_shows_welcome_at_startup(user_id: int) -> bool:
    """
    Whether the user ticked the welcome dialog's **Show at startup** box, in any of their accounts.

    The console's session asks on every page load, so the answer is cached until
    :class:`WelcomeDismissView` invalidates it.

    :param user_id: The id of the Django user.
    :type user_id: int
    :returns: True while the dialog opens by itself each time the user signs in.
    :rtype: bool
    """
    return UserProfile.objects.filter(user_id=user_id, show_welcome_at_startup=True).exists()


def welcome_opens_at_sign_in(user_id: int) -> bool:
    """
    Whether the welcome dialog opens by itself when the user signs in.

    It does until the user first closes it, and from then on while its **Show at startup** box is ticked.

    :param user_id: The id of the Django user.
    :type user_id: int
    :returns: True if the dialog opens by itself at the user's next sign-in.
    :rtype: bool
    """
    if not user_was_welcomed(user_id):
        return True
    return user_shows_welcome_at_startup(user_id)


def weather_llmclient_url(user: User) -> str | None:
    """
    The Prompt Workbench chat of the Get Weather example LLMClient, ``llm-clients/<hashed_id>/prompt/``.

    The user's own copy wins, if they have one. Otherwise, the one that their
    account, or the platform, shares with them.

    :param user: The Django user.
    :type user: django.contrib.auth.models.User
    :returns: The url path of the chat, or None if the user can't read a Get Weather LLMClient.
    :rtype: str | None
    """
    readable = LLMClient.objects.with_read_permission_for(user).filter(name=WEATHER_LLMCLIENT_NAME)
    llmclient = readable.filter(user_profile__user=user).first() or readable.order_by("id").first()
    if llmclient is None:
        return None
    return reverse(
        f"{PromptReverseNames.namespace}:{PromptReverseNames.chat_by_hashed_id}",
        kwargs={"hashed_id": llmclient.hashed_id},
    )


def not_signed_in() -> JsonResponse:
    """
    The response to a request without a signed-in user.

    :class:`~smarter.lib.django.views.SmarterAuthenticatedWebView` redirects anonymous requests to the
    login page, so this is only for a user that :func:`get_resolved_user` can't resolve.

    :returns: A 401 response.
    :rtype: django.http.JsonResponse
    """
    return JsonResponse({"error": "Not signed in."}, status=HTTPStatus.UNAUTHORIZED)


def welcome_response(user: User) -> WelcomeApiResponse:
    """
    The welcome dialog's state and links, for this user.

    :param user: The Django user.
    :type user: django.contrib.auth.models.User
    :returns: The response of the welcome dialog api views.
    :rtype: WelcomeApiResponse
    """
    return WelcomeApiResponse(
        welcomed=user_was_welcomed(user.pk),
        urls=WelcomeUrls(
            weather=weather_llmclient_url(user),
            llmclients=reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
            docs=str(smarter_settings.platform_branding_docs_url).rstrip("/"),
            project=str(smarter_settings.platform_branding_marketing_site_url).rstrip("/"),
        ),
    )


class WelcomeView(SmarterAuthenticatedWebView):
    """
    The welcome dialog's state, and the links that its last step offers.

    Response shape:

    .. code-block:: json

        {
            "welcomed": false,
            "urls": {
                "weather": "/workbench/llm-clients/3f2a9c/prompt/",
                "llmclients": "/workbench/",
                "docs": "https://docs.smarter.sh/",
                "project": "https://smarter.sh/"
            }
        }
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Return the welcome dialog's content for the user.

        :param request: The request.
        :returns: The welcome response, as JSON, or ``401`` if not signed in.
        """
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return not_signed_in()
        return JsonResponse(welcome_response(user).model_dump(mode="json"), status=HTTPStatus.OK)


class WelcomeDismissView(SmarterAuthenticatedWebView):
    """
    Records that the user has closed the welcome dialog, and whether it shows at startup.

    The body is a :class:`WelcomeDismissRequest`, as JSON; a request that isn't JSON is an empty one. It
    sets :attr:`UserProfile.welcomed_at <smarter.apps.account.models.UserProfile.welcomed_at>` on each of
    the user's profiles that hasn't got one, and keeps the date of an earlier visit, and sets
    :attr:`UserProfile.show_welcome_at_startup
    <smarter.apps.account.models.UserProfile.show_welcome_at_startup>` on each of them to
    ``showAtStartup``: false, or an empty body, and the dialog doesn't open by itself again; true, and it
    opens by itself each time the user signs in. It also sets :data:`WELCOME_SHOWN_SESSION_KEY`, so that
    the dialog doesn't open by itself again in this session. Its response is that of :class:`WelcomeView`.
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Record that the user closed the welcome dialog, and whether it shows at startup.

        Updates ``welcomed_at`` and ``show_welcome_at_startup`` on the user's profiles, and sets the
        session's welcome flag.

        :param request: The request, whose JSON body is a :class:`WelcomeDismissRequest`.
        :returns: The :class:`WelcomeView` response; ``401`` if not signed in; ``400`` if the body is
            invalid.
        """
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return not_signed_in()
        # the React app sends JSON. Any other request, e.g. an empty form post, is an empty body.
        data = request.body if request.content_type == "application/json" and request.body else b"{}"
        try:
            body = WelcomeDismissRequest.model_validate(json.loads(data))
        except (ValueError, ValidationError) as e:
            logger.warning("invalid body for user %s: %s", user.pk, e)
            return JsonResponse({"error": "Invalid request body."}, status=HTTPStatus.BAD_REQUEST)
        profiles = UserProfile.objects.filter(user=user)
        profile_ids = list(profiles.values_list("id", flat=True))
        # update(), rather than save(), so that no other field of a profile is written back.
        # the date of the first visit is kept.
        not_yet_welcomed = profiles.filter(welcomed_at__isnull=True)
        not_yet_welcomed.update(welcomed_at=timezone.now())
        profiles.update(show_welcome_at_startup=body.show_at_startup)
        for profile_id in profile_ids:
            UserProfile.get_cached_object(invalidate=True, pk=profile_id)
        user_was_welcomed.invalidate(user.pk)
        user_shows_welcome_at_startup.invalidate(user.pk)
        request.session[WELCOME_SHOWN_SESSION_KEY] = True
        logger.info(
            "welcomed user %s, show at startup: %s",
            user.pk,
            body.show_at_startup,
        )
        return JsonResponse(welcome_response(user).model_dump(mode="json"), status=HTTPStatus.OK)
