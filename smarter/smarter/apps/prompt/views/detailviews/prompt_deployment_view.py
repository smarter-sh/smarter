"""
LLMClientDeploymentView renders an llmclient's deployment, for the "Deployment" tab of Smarter Chat's Console.

The tab is in the Prompt Engineer's Workbench, between "Manifest" and "Server Logs". It shows what a browser
sees at a deployed llmclient's url, :class:`smarter.apps.llmclient.views.endpoints.LLMClientEndpointsView`,
whatever the ``enable_llmclient_endpoints_page`` waffle switch, and how to deploy an llmclient that isn't.
Its "Need to secure this url?" section manages the llmclient's api key in place: it lists the account's
api keys, creates one, and attaches or detaches it.
"""

from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin

from smarter.apps.account.models import UserProfile
from smarter.apps.llmclient.models import LLMClient, LLMClientAPIKey
from smarter.apps.llmclient.views.endpoints import deployment_context
from smarter.common.utils import to_snake_case
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])

ACTION_CREATE = "create"
"""The form action that creates an api key, and optionally attaches it."""

ACTION_ATTACH = "attach"
"""The form action that attaches an api key to the llmclient, in place of any other."""

ACTION_DETACH = "detach"
"""The form action that detaches the llmclient's api key."""

NOTICE_SUCCESS = "success"
NOTICE_DANGER = "danger"


@method_decorator(xframe_options_sameorigin, name="dispatch")
class LLMClientDeploymentView(SmarterAuthenticatedNeverCachedWebView):
    """
    Renders an llmclient's deployment alone, without the web console's header and sidebar.

    Smarter Chat, the React app of :class:`PromptWorkbenchView`, displays this page in an iframe, in its
    Console's "Deployment" tab. The page is ``llmclient/deployment.html``, the content of the page at a
    deployed llmclient's url: its status and url, where to go from here, with the integrations that put
    its chat on a web site, how to secure its url, how its url works, with curl commands, and its
    manifest. An llmclient that isn't deployed gets the url that it will have, and the command that
    deploys it.

    Its api key section posts back to this view, which enforces the rules of the
    :class:`~smarter.lib.drf.manifest.brokers.auth_token.SAMSmarterAuthTokenBroker` and of applying
    ``spec.apiKey``:

    - the api keys are those of the llmclient's account that the user may manage;
    - attaching or detaching one requires ownership of the llmclient;
    - creating one requires a staff user, and the key is the user's own. Its secret is in the response
      to that request only, never in a url or the session.

    The page is never cached, so that it shows a new deployment when the tab is reopened. It may be framed
    by the web console's own pages, of the same origin, only. An llmclient that the user may not read is
    a 404.

    **Example usage**::

        GET /workbench/llm-clients/<str:hashed_id>/deployment/
        POST /workbench/llm-clients/<str:hashed_id>/deployment/  action=attach&key_id=<uuid>
    """

    template_path = "llmclient/deployment_frame.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMClientDeploymentView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def readable_llmclient(self, request: HttpRequest, hashed_id: Optional[str]) -> Optional[LLMClient]:
        """
        The llmclient of the url's hashed id, if the user may read it, fresh from the database.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param hashed_id: The llmclient's hashed id.
        :type hashed_id: Optional[str]
        :returns: The llmclient, or None.
        :rtype: Optional[LLMClient]
        """
        llmclient_id = LLMClient.id_from_hashed_id(hashed_id) if hashed_id else None
        if not llmclient_id:
            return None
        return LLMClient.objects.filter(pk=llmclient_id).with_read_permission_for(request.user).first()  # type: ignore[attr-defined]

    def can_manage(self, request: HttpRequest, llmclient: LLMClient) -> bool:
        """
        Whether the user may attach an api key to the llmclient, or detach it: ownership of the llmclient.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :rtype: bool
        """
        return LLMClient.objects.filter(pk=llmclient.pk).with_ownership_permission_for(request.user).exists()  # type: ignore[attr-defined]

    def manageable_api_keys(self, request: HttpRequest, llmclient: LLMClient):
        """
        The api keys of the llmclient's account that the user may manage, newest first.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :returns: The api keys.
        :rtype: django.db.models.QuerySet[SmarterAuthToken]
        """
        return (
            SmarterAuthToken.objects.with_ownership_permission_for(request.user)  # type: ignore[attr-defined]
            .filter(user_profile__account=llmclient.user_profile.account)
            .order_by("-created")
        )

    def api_keys_context(
        self, request: HttpRequest, llmclient: LLMClient, can_manage: bool, can_create: bool
    ) -> SmarterDictType:
        """
        The context of the api key section: the account's api keys, the attached one, and what the user may do.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :param can_manage: Whether the user may attach and detach api keys.
        :type can_manage: bool
        :param can_create: Whether the user may create an api key.
        :type can_create: bool
        :returns: The context.
        :rtype: SmarterDictType
        """
        attached = LLMClientAPIKey.objects.filter(llmclient=llmclient).select_related("api_key").first()
        attached_key = attached.api_key if attached else None
        api_keys = [
            {
                "key_id": str(api_key.key_id),
                "name": api_key.name,
                "description": api_key.description or "",
                "is_active": api_key.is_active,
                "owner": api_key.user.username,
                "last_used_at": api_key.last_used_at,
                "is_attached": attached_key is not None and api_key.pk == attached_key.pk,
            }
            for api_key in self.manageable_api_keys(request, llmclient)
        ]
        return {
            "api_keys": api_keys,
            "attached_api_key": (
                {"name": attached_key.name, "is_active": attached_key.is_active} if attached_key else None
            ),
            "can_manage_api_keys": can_manage,
            "can_create_api_keys": can_create,
        }

    def render_page(
        self,
        request: HttpRequest,
        llmclient: LLMClient,
        notice: Optional[SmarterDictType] = None,
        new_api_key: Optional[SmarterDictType] = None,
        status: int = 200,
    ) -> HttpResponse:
        """
        Render the page.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :param notice: A message about the form's action: ``level`` (success or danger) and ``text``.
        :type notice: Optional[SmarterDictType]
        :param new_api_key: An api key that was just created: its ``name`` and ``secret``, shown once.
        :type new_api_key: Optional[SmarterDictType]
        :param status: The http status.
        :type status: int
        :returns: The page.
        :rtype: django.http.HttpResponse
        """
        context = deployment_context(llmclient)
        context["standalone"] = False
        context.update(
            self.api_keys_context(
                request, llmclient, can_manage=self.can_manage(request, llmclient), can_create=request.user.is_staff  # type: ignore[union-attr]
            )
        )
        context["api_key_notice"] = notice
        context["new_api_key"] = new_api_key
        context["api_key_actions"] = {"create": ACTION_CREATE, "attach": ACTION_ATTACH, "detach": ACTION_DETACH}
        # rendered as is, not minified: the minifier drops whitespace-only text, which is the indentation
        # between the highlighted spans of the manifest's YAML.
        return render(request=request, template_name=self.template_path, context=context, status=status)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The page, for the llmclient of the url's hashed id.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: The page, or a 404 if the user may not read the llmclient, or there is none.
        :rtype: django.http.HttpResponse
        """
        llmclient = self.readable_llmclient(request, kwargs.get("hashed_id"))
        if llmclient is None:
            logger.debug(
                "%s.get() no llmclient %s for %s", self.formatted_class_name, kwargs.get("hashed_id"), request.user
            )
            return SmarterHttpResponseNotFound(request=request, error_message="LLMClient not found.")
        logger.debug("%s.get() deployment of %s", self.formatted_class_name, llmclient)
        return self.render_page(request, llmclient)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Create an api key, or attach one to the llmclient, or detach it, then render the page.

        :param request: The request, whose ``action`` is ``create`` (with ``name``, ``description`` and
            ``attach``), ``attach`` (with ``key_id``) or ``detach``.
        :type request: django.http.HttpRequest
        :returns: The page, with a notice, and a new api key's secret; 400 for an invalid form, 403 for
            an action that the user may not take, or 404 if the user may not read the llmclient.
        :rtype: django.http.HttpResponse
        """
        llmclient = self.readable_llmclient(request, kwargs.get("hashed_id"))
        if llmclient is None:
            return SmarterHttpResponseNotFound(request=request, error_message="LLMClient not found.")
        action = request.POST.get("action")
        if action == ACTION_CREATE:
            return self.create_api_key(request, llmclient)
        if action not in (ACTION_ATTACH, ACTION_DETACH):
            return self.render_page(
                request, llmclient, {"level": NOTICE_DANGER, "text": _("Unknown action.")}, status=400
            )
        if not self.can_manage(request, llmclient):
            return self.render_page(
                request,
                llmclient,
                {
                    "level": NOTICE_DANGER,
                    "text": _("Only the LLMClient's owner, or an account admin, can change its api key."),
                },
                status=403,
            )
        if action == ACTION_DETACH:
            LLMClientAPIKey.detach(llmclient)
            logger.info("%s.post() %s detached the api key of %s", self.formatted_class_name, request.user, llmclient)
            return self.render_page(
                request,
                llmclient,
                {"level": NOTICE_SUCCESS, "text": _("The api key is detached. The LLMClient's url is public again.")},
            )

        api_key = self.manageable_api_keys(request, llmclient).filter(key_id=request.POST.get("key_id") or None).first()
        if api_key is None:
            return self.render_page(
                request, llmclient, {"level": NOTICE_DANGER, "text": _("That api key was not found.")}, status=400
            )
        LLMClientAPIKey.attach(llmclient, api_key)
        logger.info(
            "%s.post() %s attached api key %s to %s", self.formatted_class_name, request.user, api_key.name, llmclient
        )
        return self.render_page(
            request,
            llmclient,
            {
                "level": NOTICE_SUCCESS,
                "text": _("%(name)s is attached. Every request to the LLMClient's url now needs it.")
                % {"name": api_key.name},
            },
        )

    def create_api_key(self, request: HttpRequest, llmclient: LLMClient) -> HttpResponse:
        """
        Create an api key for the user, which must be staff, and attach it to the llmclient if asked to.

        :param request: The request, with ``name``, ``description``, and ``attach``.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :returns: The page, with the new key's secret, shown once.
        :rtype: django.http.HttpResponse
        """
        user = request.user
        if not user.is_staff:  # type: ignore[union-attr]
            return self.render_page(
                request,
                llmclient,
                {"level": NOTICE_DANGER, "text": _("Only an account admin can create api keys.")},
                status=403,
            )
        name = to_snake_case((request.POST.get("name") or "").strip())
        if not name or not SmarterValidator.is_valid_snake_case(name):
            return self.render_page(
                request,
                llmclient,
                {"level": NOTICE_DANGER, "text": _("Give the api key a name, in snake_case, e.g. my_site_chat.")},
                status=400,
            )
        user_profile = UserProfile.objects.filter(user=user, account=llmclient.user_profile.account).first()
        if user_profile is None:
            return self.render_page(
                request,
                llmclient,
                {
                    "level": NOTICE_DANGER,
                    "text": _("Only an admin of the LLMClient's account can create its api keys."),
                },
                status=403,
            )
        if SmarterAuthToken.objects.filter(user=user, name=name).exists():
            return self.render_page(
                request,
                llmclient,
                {"level": NOTICE_DANGER, "text": _("You already have an api key named %(name)s.") % {"name": name}},
                status=400,
            )
        api_key, secret = SmarterAuthToken.objects.create(
            user=user,
            user_profile=user_profile,
            name=name,
            description=(request.POST.get("description") or "").strip()[:255] or None,
        )
        logger.info("%s.create_api_key() %s created api key %s", self.formatted_class_name, user, api_key.name)
        text = _("%(name)s is created.") % {"name": api_key.name}
        if request.POST.get("attach") and self.can_manage(request, llmclient):
            LLMClientAPIKey.attach(llmclient, api_key)
            text = _("%(name)s is created, and attached. Every request to the LLMClient's url now needs it.") % {
                "name": api_key.name
            }
        return self.render_page(
            request,
            llmclient,
            {"level": NOTICE_SUCCESS, "text": text},
            new_api_key={"name": api_key.name, "secret": secret},
        )
