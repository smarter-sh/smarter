"""
LLMClientDeploymentView renders an llmclient's deployment, for the "Deployment" tab of the workbench's Console.

The tab is in the Prompt Engineer's Workbench, between "Manifest" and "Server Logs". It shows what a browser
sees at a deployed llmclient's url, :class:`smarter.apps.llmclient.views.endpoints.LLMClientEndpointsView`,
whatever the ``enable_llmclient_endpoints_page`` waffle switch, and how to deploy an llmclient that isn't.
Both show the ``@smarter/llmclient-deployment`` React app's page, whose contract is
:mod:`smarter.apps.llmclient.views.deployment_contract`. The workbench, the ``@smarter/workbench`` React
app, renders it as a component, and fetches its data from :class:`LLMClientDeploymentView` when the tab is
first opened. The tab adds the llmclient's owner, and its "Need to secure this url?" section manages the
llmclient's api key in place, with the api views of this module: they create an api key, and attach it,
or detach it.
"""

from http import HTTPStatus
from typing import Optional

from django.http import HttpRequest, HttpResponse, JsonResponse
from pydantic import BaseModel, ValidationError

from smarter.apps.account.models import UserProfile
from smarter.apps.llmclient.models import LLMClient, LLMClientAPIKey
from smarter.apps.llmclient.views.deployment_contract import (
    ApiKeyActionResponse,
    AttachApiKeyRequest,
    CreateApiKeyRequest,
    DeploymentApiKey,
    DeploymentApiKeys,
    DeploymentAttachedApiKey,
    DeploymentOwnership,
    ErrorCode,
    ErrorResponse,
    LLMClientDeploymentPage,
    NewApiKey,
)
from smarter.apps.llmclient.views.endpoints import deployment_page
from smarter.common.utils import to_snake_case
from smarter.lib import json, logging
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])

OWNERSHIP_DOCS_URL = "https://docs.smarter.sh/en/latest/smarter-resources/account/models/metadata_with_ownership.html"
"""The docs page that explains who owns a Smarter resource, and who may read and change it."""


class DeploymentApiError(Exception):
    """An api key action that failed: its code, which the React app explains, its message, and its status."""

    def __init__(self, code: ErrorCode, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.code: ErrorCode = code
        self.message = message
        self.status = status


def readable_llmclient(request: HttpRequest, hashed_id: Optional[str]) -> Optional[LLMClient]:
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


def can_manage(request: HttpRequest, llmclient: LLMClient) -> bool:
    """
    Whether the user may attach an api key to the llmclient, or detach it: ownership of the llmclient.

    :param request: The request.
    :type request: django.http.HttpRequest
    :param llmclient: The llmclient.
    :type llmclient: LLMClient
    :rtype: bool
    """
    return LLMClient.objects.filter(pk=llmclient.pk).with_ownership_permission_for(request.user).exists()  # type: ignore[attr-defined]


def manageable_api_keys(request: HttpRequest, llmclient: LLMClient):
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


def api_keys_section(request: HttpRequest, llmclient: LLMClient, manage: bool) -> DeploymentApiKeys:
    """
    The api key section: the account's api keys, the attached one, what the user may do, and where.

    :param request: The request.
    :type request: django.http.HttpRequest
    :param llmclient: The llmclient.
    :type llmclient: LLMClient
    :param manage: Whether the user may attach and detach api keys.
    :type manage: bool
    :returns: The section.
    :rtype: DeploymentApiKeys
    """
    # pylint: disable=C0415
    from smarter.apps.prompt.urls import PromptReverseNames

    attached = LLMClientAPIKey.objects.filter(llmclient=llmclient).select_related("api_key").first()
    attached_key = attached.api_key if attached else None
    hashed_id = llmclient.hashed_id

    def url(name: str) -> str:
        return reverse(f"{PromptReverseNames.namespace}:{name}", kwargs={"hashed_id": hashed_id})

    return DeploymentApiKeys(
        api_keys=[
            DeploymentApiKey(
                key_id=api_key.key_id,
                name=api_key.name,
                description=api_key.description or "",
                is_active=api_key.is_active,
                owner=api_key.user.username,
                last_used_at=api_key.last_used_at,
                is_attached=attached_key is not None and api_key.pk == attached_key.pk,
            )
            for api_key in manageable_api_keys(request, llmclient).select_related("user")
        ],
        attached=(
            DeploymentAttachedApiKey(name=attached_key.name, is_active=attached_key.is_active) if attached_key else None
        ),
        can_manage=manage,
        can_create=bool(request.user.is_staff),  # type: ignore[union-attr]
        create_url=url(PromptReverseNames.deployment_api_key_create_by_hashed_id),
        attach_url=url(PromptReverseNames.deployment_api_key_attach_by_hashed_id),
        detach_url=url(PromptReverseNames.deployment_api_key_detach_by_hashed_id),
    )


def ownership_section(llmclient: LLMClient, manage: bool) -> DeploymentOwnership:
    """
    Who owns the llmclient, and where a user who may not change it can clone it.

    The owner is in the workbench's tab only, never on the page at the deployed llmclient's url, which
    anyone can open.

    :param llmclient: The llmclient.
    :type llmclient: LLMClient
    :param manage: Whether the user has ownership permission for the llmclient: its owner, an admin of
        its account, or a superuser.
    :type manage: bool
    :returns: The section.
    :rtype: DeploymentOwnership
    """
    # pylint: disable=C0415
    from smarter.apps.prompt.urls import PromptReverseNames

    owner = llmclient.user_profile.user
    full_name = owner.get_full_name()
    return DeploymentOwnership(
        owner=f"{full_name} ({owner.username})" if full_name else owner.username,
        can_edit=manage,
        llmclient_list_url=reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
        ownership_docs_url=OWNERSHIP_DOCS_URL,
    )


def workbench_page(request: HttpRequest, llmclient: LLMClient) -> LLMClientDeploymentPage:
    """
    The llmclient's deployment page, as the workbench's tab shows it: with its owner and api keys.

    :param request: The request.
    :type request: django.http.HttpRequest
    :param llmclient: The llmclient.
    :type llmclient: LLMClient
    :returns: The page.
    :rtype: LLMClientDeploymentPage
    """
    manage = can_manage(request, llmclient)
    return deployment_page(llmclient).model_copy(
        update={
            "mode": "workbench",
            "ownership": ownership_section(llmclient, manage),
            "api_keys": api_keys_section(request, llmclient, manage),
        }
    )


class LLMClientDeploymentView(SmarterAuthenticatedNeverCachedWebView):
    """
    Returns an llmclient's deployment page, as JSON, for the "Deployment" tab of the Prompt Engineer's Workbench.

    The workbench, the ``@smarter/workbench`` React app of :class:`PromptWorkbenchView`, fetches it when the
    tab is first opened, and renders it with the ``@smarter/llmclient-deployment`` component, in its
    workbench mode. The data is :func:`workbench_page`: the page at a deployed llmclient's url, with the
    llmclient's owner, a guide to cloning it for a user who may not change it, and its api keys. An
    llmclient that isn't deployed gets the url that it will have, and the command that deploys it.

    The response is never cached, so that the tab shows a new deployment when the workbench is reloaded.
    An llmclient that the user may not read is a 404.

    **Example usage**::

        GET /workbench/llm-clients/<str:hashed_id>/deployment/
    """

    http_method_names = ["get"]

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMClientDeploymentView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The page's data, an :class:`~smarter.apps.llmclient.views.deployment_contract.LLMClientDeploymentPage`.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: The page's data, or an ErrorResponse, a 404, if the user may not read the llmclient, or there
            is none.
        :rtype: django.http.JsonResponse
        """
        llmclient = readable_llmclient(request, kwargs.get("hashed_id"))
        if llmclient is None:
            logger.debug(
                "%s.get() no llmclient %s for %s", self.formatted_class_name, kwargs.get("hashed_id"), request.user
            )
            error = ErrorResponse(error="LLMClient not found.", code="not_found")
            return JsonResponse(error.to_json(), status=HTTPStatus.NOT_FOUND)
        logger.debug("%s.get() deployment of %s", self.formatted_class_name, llmclient)
        return JsonResponse(workbench_page(request, llmclient).to_json())


class LLMClientDeploymentApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    The base class of the "Deployment" tab's api key actions: POST only, JSON in and out.

    Each enforces the rules of the
    :class:`~smarter.lib.drf.manifest.brokers.auth_token.SAMSmarterAuthTokenBroker` and of applying
    ``spec.apiKey``:

    - the api keys are those of the llmclient's account that the user may manage;
    - attaching or detaching one requires ownership of the llmclient;
    - creating one requires a staff user, and the key is the user's own. Its secret is in the response
      to that request only.

    A success is an :class:`~smarter.apps.llmclient.views.deployment_contract.ApiKeyActionResponse`, the
    page as it now is. A failure is an
    :class:`~smarter.apps.llmclient.views.deployment_contract.ErrorResponse`, whose code the React app
    explains in the user's language. An llmclient that the user may not read is a 404.

    Subclasses implement :meth:`handle`, and set :attr:`request_model` if the request has a body.
    """

    request_model: Optional[type[BaseModel]] = None
    http_method_names = ["post"]

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        return self.formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    def parse(self, request: HttpRequest) -> Optional[BaseModel]:
        """
        Validate the request's JSON body with :attr:`request_model`.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: The request's model, or None if the action has no body.
        :rtype: Optional[pydantic.BaseModel]
        :raises DeploymentApiError: If the body isn't valid.
        """
        if self.request_model is None:
            return None
        try:
            body = json.loads(request.body or b"{}")
            return self.request_model.model_validate(body if isinstance(body, dict) else {})
        except (json.JSONDecodeError, ValidationError) as e:
            raise DeploymentApiError("invalid_request", f"The request is not valid: {e}") from e

    def require_manage(self, request: HttpRequest, llmclient: LLMClient) -> None:
        """
        Require ownership of the llmclient.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :raises DeploymentApiError: If the user may not change its api key.
        """
        if not can_manage(request, llmclient):
            raise DeploymentApiError(
                "not_owner",
                "Only the LLMClient's owner, or an account admin, can change its api key.",
                HTTPStatus.FORBIDDEN,
            )

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Carry out the action, and return the page as it now is.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: An ApiKeyActionResponse, or an ErrorResponse.
        :rtype: django.http.JsonResponse
        """
        llmclient = readable_llmclient(request, kwargs.get("hashed_id"))
        try:
            if llmclient is None:
                raise DeploymentApiError("not_found", "LLMClient not found.", HTTPStatus.NOT_FOUND)
            new_api_key = self.handle(request, llmclient, self.parse(request))
        except DeploymentApiError as e:
            logger.debug("%s.post() %s: %s", self.formatted_class_name, e.code, e.message)
            return JsonResponse(ErrorResponse(error=e.message, code=e.code).to_json(), status=e.status)
        response = ApiKeyActionResponse(page=workbench_page(request, llmclient), new_api_key=new_api_key)
        return JsonResponse(response.to_json())

    def handle(self, request: HttpRequest, llmclient: LLMClient, body: Optional[BaseModel]) -> Optional[NewApiKey]:
        """
        Carry out the action.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param llmclient: The llmclient.
        :type llmclient: LLMClient
        :param body: The request's model, if it has a body.
        :type body: Optional[pydantic.BaseModel]
        :returns: A new api key's name and secret, if the action created one.
        :rtype: Optional[NewApiKey]
        :raises DeploymentApiError: If the action fails.
        """
        raise NotImplementedError


class LLMClientDeploymentApiKeyCreateView(LLMClientDeploymentApiView):
    """
    Create an api key for the user, which must be staff, and attach it to the llmclient if asked to.

    **Example usage**::

        POST /workbench/llm-clients/<str:hashed_id>/deployment/api-keys/create/
        {"name": "my_site_chat", "description": "The chat on www.example.com", "attach": true}
    """

    request_model = CreateApiKeyRequest

    def handle(self, request: HttpRequest, llmclient: LLMClient, body: Optional[BaseModel]) -> Optional[NewApiKey]:
        assert isinstance(body, CreateApiKeyRequest)  # nosec B101: request_model is CreateApiKeyRequest.
        user = request.user
        if not user.is_staff:  # type: ignore[union-attr]
            raise DeploymentApiError("not_admin", "Only an account admin can create api keys.", HTTPStatus.FORBIDDEN)
        name = to_snake_case(body.name.strip())
        if not name or not SmarterValidator.is_valid_snake_case(name):
            raise DeploymentApiError("invalid_name", "Give the api key a name, in snake_case, e.g. my_site_chat.")
        user_profile = UserProfile.objects.filter(user=user, account=llmclient.user_profile.account).first()
        if user_profile is None:
            raise DeploymentApiError(
                "not_account_admin",
                "Only an admin of the LLMClient's account can create its api keys.",
                HTTPStatus.FORBIDDEN,
            )
        if SmarterAuthToken.objects.filter(user=user, name=name).exists():
            raise DeploymentApiError("duplicate_name", f"You already have an api key named {name}.")
        attach = body.attach and can_manage(request, llmclient)
        api_key, secret = SmarterAuthToken.objects.create(
            user=user,
            user_profile=user_profile,
            name=name,
            description=body.description.strip()[:255] or None,
        )
        logger.info("%s.handle() %s created api key %s", self.formatted_class_name, user, api_key.name)
        if attach:
            LLMClientAPIKey.attach(llmclient, api_key)
            logger.info(
                "%s.handle() %s attached api key %s to %s", self.formatted_class_name, user, api_key.name, llmclient
            )
        return NewApiKey(name=api_key.name, secret=secret)


class LLMClientDeploymentApiKeyAttachView(LLMClientDeploymentApiView):
    """
    Attach one of the account's api keys to the llmclient, in place of any other.

    **Example usage**::

        POST /workbench/llm-clients/<str:hashed_id>/deployment/api-keys/attach/
        {"keyId": "<uuid>"}
    """

    request_model = AttachApiKeyRequest

    def handle(self, request: HttpRequest, llmclient: LLMClient, body: Optional[BaseModel]) -> Optional[NewApiKey]:
        assert isinstance(body, AttachApiKeyRequest)  # nosec B101: request_model is AttachApiKeyRequest.
        self.require_manage(request, llmclient)
        api_key = manageable_api_keys(request, llmclient).filter(key_id=body.key_id).first()
        if api_key is None:
            raise DeploymentApiError("api_key_not_found", "That api key was not found.")
        LLMClientAPIKey.attach(llmclient, api_key)
        logger.info(
            "%s.handle() %s attached api key %s to %s", self.formatted_class_name, request.user, api_key.name, llmclient
        )
        return None


class LLMClientDeploymentApiKeyDetachView(LLMClientDeploymentApiView):
    """
    Detach the llmclient's api key, which makes its url public again.

    **Example usage**::

        POST /workbench/llm-clients/<str:hashed_id>/deployment/api-keys/detach/
    """

    def handle(self, request: HttpRequest, llmclient: LLMClient, body: Optional[BaseModel]) -> Optional[NewApiKey]:
        self.require_manage(request, llmclient)
        LLMClientAPIKey.detach(llmclient)
        logger.info("%s.handle() %s detached the api key of %s", self.formatted_class_name, request.user, llmclient)
        return None
