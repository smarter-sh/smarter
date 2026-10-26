"""
The page that a browser sees at a deployed LLMClient's endpoints.

A deployed LLMClient's endpoints, ``/config/`` and ``/prompt/``, are api endpoints that answer only POST.
A browser that opens one of them, or the LLMClient's default url, instead receives a page about the
LLMClient and The Smarter Project: what its url is and how it works, the curl commands that call the
endpoints, the ways to put its chat on a web site, the LLMClient's manifest, without the personal
information in it, and how to build one. The page is served only while the
``enable_llmclient_endpoints_page`` waffle switch is active.

The Prompt Engineer's Workbench shows the same content, whatever the switch, in the "Deployment" tab of
its Console: see
:class:`smarter.apps.prompt.views.detailviews.prompt_deployment_view.LLMClientDeploymentView`. Both
render the ``@smarter/llmclient-deployment`` React package's page, this one as its app, the workbench
as its component, and both build its data with :func:`deployment_page`, whose contract is
:mod:`smarter.apps.llmclient.views.deployment_contract`.

.. seealso::

    - :mod:`smarter.urls.llmclients`
    - :mod:`smarter.urls.console`, which serves LLMClients on their custom domains
"""

from functools import wraps
from typing import Callable, Optional
from urllib.parse import urljoin

import yaml
from cache_results import cache_results
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import render

from smarter.apps.llmclient.manifest.models.llmclient.const import MANIFEST_KIND
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient, get_cached_llmclient_by_request
from smarter.apps.llmclient.templatetags.react_llmclient_deployment import (
    DEPLOYMENT_DATA_ID,
    DEPLOYMENT_ROOT_ID,
)
from smarter.apps.llmclient.views.deployment_contract import (
    DeploymentLinks,
    DeploymentLLMClient,
    DeploymentSnippets,
    LLMClientDeploymentPage,
)
from smarter.apps.prompt.contract.models import (
    PromptChatApiConfigRequest,
    PromptChatApiMessage,
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
    PromptChatApiPromptResult,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_PRODUCT_DESCRIPTION, SMARTER_PRODUCT_NAME
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterWebHtmlView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])
logger_prefix = logging.formatted_text(__name__)

EXAMPLE_PROMPT = "hello world"
"""The prompt that the page's example ``/prompt/`` command sends, for an LLMClient without example prompts."""

SESSION_KEY_PLACEHOLDER = "<SESSION-KEY>"
"""The placeholder of a chat session's key in the page's commands, which the config api's response replaces."""

EXAMPLE_RESPONSE_CONTENT = (
    "## The LLM's answer\n\nIn **Markdown**: headings, lists, `code`, tables and [links](https://smarter.sh)."
)
"""The assistant message's content in the page's example ``/prompt/`` response."""

EMBED_SCRIPT_URL = "https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
"""Smarter Chat's embed script, on jsDelivr, which the page's html snippet loads."""

ALLOWED_ORIGINS_YAML = """spec:
  config:
    prompt:
      allowedOrigins:
        - https://www.example.com"""
"""The part of an LLMClient's manifest that allows a web site's origin to call it."""

DRUPAL_INSTALL_COMMANDS = """composer config repositories.smarter-drupal vcs https://github.com/smarter-sh/smarter-drupal
composer require smarter-sh/smarter-drupal
drush pm:install smarter_chat"""
"""The commands that install Smarter Chat for Drupal."""

NPM_INSTALL_COMMAND = "npm install @smarter.sh/ui-chat"
"""The command that installs Smarter Chat's npm package."""

API_KEY_YAML = """spec:
  apiKey: <API-KEY-NAME>"""
"""The part of an LLMClient's manifest that attaches an api key to it, by the key's name."""

SWITCH_COMMAND = "python manage.py waffle_switch enable_llmclient_endpoints_page off"
"""The command that turns off the page at deployed LLMClients' urls, which the page shows administrators."""

LOGO_PATH = "images/logo/smarter-crop.png"
"""The Smarter Project's logo, on its cdn."""

BROWSER_METHODS = ("GET", "HEAD")
"""The methods that :func:`browser_friendly` sends to :class:`LLMClientEndpointsView`."""

MANIFEST_PII_EXCLUDE = {"status": {"username"}}
"""
The fields that :func:`manifest_yaml` leaves out of the page's manifest: the personal information in it.

``status.username`` is the owner's username.
"""

MANIFEST_CACHE_TIMEOUT = 600
"""How long, in seconds, :func:`cached_manifest_yaml` keeps a manifest."""


def example_prompt(llmclient: LLMClient) -> str:
    """
    The prompt that the page's example ``/prompt/`` command sends: the LLMClient's first example prompt.

    :param llmclient: The LLMClient.
    :type llmclient: smarter.apps.llmclient.models.LLMClient
    :returns: Its first non-empty example prompt, or :data:`EXAMPLE_PROMPT` if it has none.
    :rtype: str
    """
    for prompt in llmclient.app_example_prompts or []:
        if isinstance(prompt, str) and prompt.strip():
            return prompt.strip()
    return EXAMPLE_PROMPT


def curl_command(url: str, body: str = "", authenticated: bool = False) -> str:
    """
    A curl command that POSTs to a deployed LLMClient's endpoint, one option per line.

    :param url: The endpoint's url.
    :type url: str
    :param body: The JSON request body, or empty for none. It is quoted for a POSIX shell.
    :type body: str
    :param authenticated: True to send an api key, which an LLMClient with api keys requires.
    :type authenticated: bool
    :returns: The command.
    :rtype: str
    """
    lines = [f"curl -X POST {url}", '-H "Content-Type: application/json"']
    if authenticated:
        lines.append('-H "Authorization: Token <YOUR-API-KEY>"')
    if body:
        quoted = body.replace("'", "'\\''")
        lines.append(f"-d '{quoted}'")
    return " \\\n  ".join(lines)


def example_response() -> str:
    """
    An example of the ``/prompt/`` endpoint's response, abbreviated to the assistant's Markdown message.

    It is built from the chat api contract's model, so that it can't drift from the real response.

    :returns: The response, as indented JSON.
    :rtype: str
    """
    response = PromptChatApiPromptResponse(
        api="smarter.sh/v1",
        data=PromptChatApiPromptResult(
            status=200, messages=[PromptChatApiMessage(role="assistant", content=EXAMPLE_RESPONSE_CONTENT)]
        ),
    )
    return response.model_dump_json(indent=2, exclude_none=True, include={"api": True, "data": {"status", "messages"}})


def embed_html(url: str, authenticated: bool = False) -> str:
    """
    The html that adds the LLMClient's chat to any web page: Smarter Chat's embed script, as a launcher.

    :param url: The LLMClient's url.
    :type url: str
    :param authenticated: True to pass an api key, which an LLMClient with api keys requires.
    :type authenticated: bool
    :returns: The html.
    :rtype: str
    """
    lines = [f'<script src="{EMBED_SCRIPT_URL}"', f'  data-chatbot="{url}/"']
    if authenticated:
        lines.append('  data-api-key="<YOUR-API-KEY>"')
    return "\n".join(lines) + " async></script>"


def react_snippet(url: str, authenticated: bool = False) -> str:
    """
    A React component that displays the LLMClient's chat, with Smarter Chat's npm package.

    :param url: The LLMClient's url.
    :type url: str
    :param authenticated: True to pass an api key, which an LLMClient with api keys requires.
    :type authenticated: bool
    :returns: The component's TypeScript.
    :rtype: str
    """
    api_key = "\n        apiKey={import.meta.env.VITE_SMARTER_API_KEY}" if authenticated else ""
    return (
        'import { SmarterChat } from "@smarter.sh/ui-chat";\n'
        'import "@smarter.sh/ui-chat/dist/ui-chat.css";\n'
        'import "katex/dist/katex.min.css";\n'
        "\n"
        "export default function Chat() {\n"
        "  return (\n"
        "    <div style={{ height: 600 }}>\n"
        "      <SmarterChat\n"
        f'        apiUrl="{url}/"{api_key}\n'
        "        showConsole={false}\n"
        "      />\n"
        "    </div>\n"
        "  );\n"
        "}"
    )


def llmclient_manifest(llmclient: LLMClient) -> SAMLLMClient:
    """
    The LLMClient's manifest, as ``smarter describe llmclient`` returns it, from its broker.

    :param llmclient: The LLMClient.
    :type llmclient: smarter.apps.llmclient.models.LLMClient
    :returns: The manifest.
    :rtype: smarter.apps.llmclient.manifest.models.llmclient.model.SAMLLMClient
    :raises SAMLLMClientBrokerError: If the broker can't build it.
    """
    # pylint: disable=C0415
    from smarter.apps.llmclient.manifest.brokers.llmclient import (
        SAMLLMClientBroker,
        SAMLLMClientBrokerError,
    )

    broker = SAMLLMClientBroker(None, name=llmclient.name, kind=MANIFEST_KIND, user_profile=llmclient.user_profile)
    data = broker.django_orm_to_manifest_dict()
    if data is None:
        raise SAMLLMClientBrokerError(f"The manifest of {llmclient} could not be built.", thing=MANIFEST_KIND)
    return SAMLLMClient.model_validate(data)


class _ManifestDumper(yaml.SafeDumper):
    """A YAML dumper that writes multi-line strings, e.g. a system prompt, as literal blocks."""


def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_ManifestDumper.add_representer(str, _represent_str)


def manifest_yaml(manifest: SAMLLMClient) -> str:
    """
    The manifest as YAML, in the order of its model's fields, without :data:`MANIFEST_PII_EXCLUDE`.

    :param manifest: The manifest.
    :type manifest: smarter.apps.llmclient.manifest.models.llmclient.model.SAMLLMClient
    :returns: The YAML.
    :rtype: str
    """
    data = manifest.model_dump(mode="json", exclude_none=True, exclude=MANIFEST_PII_EXCLUDE)
    return yaml.dump(data, Dumper=_ManifestDumper, sort_keys=False, allow_unicode=True, width=100)


@cache_results(timeout=MANIFEST_CACHE_TIMEOUT)
def cached_manifest_yaml(llmclient_id: int, updated_at: str) -> str:
    """
    The YAML of an LLMClient's manifest, for the page, which its broker takes about a second to build.

    An update of the LLMClient changes ``updated_at``, and so the key. A change to a resource that it
    refers to, e.g. a plugin added to it, shows after :data:`MANIFEST_CACHE_TIMEOUT`.

    :param llmclient_id: The LLMClient's id.
    :type llmclient_id: int
    :param updated_at: The LLMClient's ``updated_at``, in ISO 8601.
    :type updated_at: str
    :returns: The YAML.
    :rtype: str
    :raises SAMLLMClientBrokerError: If the broker can't build the manifest, which is then not cached.
    """
    return manifest_yaml(llmclient_manifest(LLMClient.objects.get(pk=llmclient_id)))


def create_api_key_command(account_number: str, llmclient_name: str) -> str:
    """
    The command that a platform administrator runs to create an api key, which prints its secret once.

    :param account_number: The LLMClient's account number.
    :type account_number: str
    :param llmclient_name: The LLMClient's name, for the key's description.
    :type llmclient_name: str
    :returns: The command, one option per line.
    :rtype: str
    """
    return (
        "python manage.py create_api_key \\\n"
        f"  --account_number {account_number} \\\n"
        "  --username <YOUR-USERNAME> \\\n"
        f'  --description "{llmclient_name} in production"'
    )


def api_keys_url() -> str:
    """
    The url of the web console's API Keys page, which lists the account's api keys, and turns them on and off.

    It is absolute, on the platform's domain, because the page at a deployed LLMClient's url is on the
    LLMClient's own host, whose urlconf has none of the web console's names.

    :returns: The url.
    :rtype: str
    """
    # pylint: disable=C0415
    from smarter.lib.drf.urls import AuthTokenReverseNames

    path = reverse(AuthTokenReverseNames.namespace, AuthTokenReverseNames.listview, urlconf=settings.ROOT_URLCONF)
    return urljoin(smarter_settings.environment_url, path)


def deployment_page(llmclient: LLMClient) -> LLMClientDeploymentPage:
    """
    The data of the LLMClient's deployment page: the LLMClient, its url, and the snippets that call it.

    An LLMClient that isn't deployed has the url that it will have once it is, and ``deployed`` is false.
    The page is the workbench's, without its owner or api keys, which
    :class:`~smarter.apps.prompt.views.detailviews.prompt_deployment_view.LLMClientDeploymentView` adds.
    The page at the LLMClient's url is its :meth:`~LLMClientDeploymentPage.public` copy.

    :param llmclient: The LLMClient.
    :type llmclient: smarter.apps.llmclient.models.LLMClient
    :returns: The page.
    :rtype: smarter.apps.llmclient.views.deployment_contract.LLMClientDeploymentPage
    """
    deployed = bool(llmclient.deployed)
    base_url = (llmclient.url if deployed else llmclient.custom_url or llmclient.default_url).rstrip("/")
    authenticated = llmclient.is_authentication_required
    prompt = PromptChatApiPromptRequest(messages=[PromptChatApiMessage(role="user", content=example_prompt(llmclient))])
    manifest: Optional[str] = None
    try:
        manifest = cached_manifest_yaml(llmclient.pk, llmclient.updated_at.isoformat())
    # the page, without the manifest, rather than an error. pylint: disable=W0718
    except Exception as e:
        logger.warning("%s.deployment_page() could not build the manifest of %s: %s", logger_prefix, llmclient, e)
    return LLMClientDeploymentPage(
        mode="workbench",
        llmclient=DeploymentLLMClient(
            name=llmclient.name,
            app_name=llmclient.app_name or llmclient.name,
            example_prompts=[prompt for prompt in llmclient.app_example_prompts or [] if isinstance(prompt, str)],
            provider=llmclient.provider or None,
            model=llmclient.default_model or None,
            version=llmclient.version or None,
            url=base_url,
            workbench_url=llmclient.workbench_url,
        ),
        deployed=deployed,
        authenticated=authenticated,
        manifest_yaml=manifest,
        snippets=DeploymentSnippets(
            deploy_command=f"smarter deploy llmclient {llmclient.name}",
            deploy_commands=f"smarter apply -f {llmclient.name}.yaml\nsmarter deploy llmclient {llmclient.name}",
            config_command=curl_command(f"{base_url}/config/", authenticated=authenticated),
            prompt_command=curl_command(
                f"{base_url}/prompt/",
                body=prompt.model_dump_json(exclude_none=True),
                authenticated=authenticated,
            ),
            session_config_command=curl_command(
                f"{base_url}/config/",
                body=PromptChatApiConfigRequest(session_key=SESSION_KEY_PLACEHOLDER).model_dump_json(),
                authenticated=authenticated,
            ),
            session_prompt_command=curl_command(
                f"{base_url}/prompt/",
                body=prompt.model_copy(update={"session_key": SESSION_KEY_PLACEHOLDER}).model_dump_json(
                    exclude_none=True
                ),
                authenticated=authenticated,
            ),
            example_response=example_response(),
            allowed_origins_yaml=ALLOWED_ORIGINS_YAML,
            api_key_yaml=API_KEY_YAML,
            drupal_install_commands=DRUPAL_INSTALL_COMMANDS,
            npm_install_command=NPM_INSTALL_COMMAND,
            embed_html=embed_html(base_url, authenticated=authenticated),
            embed_html_with_api_key=embed_html(base_url, authenticated=True),
            react_snippet=react_snippet(base_url, authenticated=authenticated),
            react_snippet_with_api_key=react_snippet(base_url, authenticated=True),
            create_api_key_command=create_api_key_command(
                llmclient.user_profile.account.account_number, llmclient.name
            ),
            switch_command=SWITCH_COMMAND,
        ),
        links=DeploymentLinks(
            api_keys_url=api_keys_url(),
            marketing_site_url=str(smarter_settings.marketing_site_url),
            docs_url=str(smarter_settings.smarter_project_docs_url),
            logo_url=urljoin(str(smarter_settings.smarter_project_cdn_url), LOGO_PATH),
            product_name=SMARTER_PRODUCT_NAME,
            product_description=SMARTER_PRODUCT_DESCRIPTION,
        ),
    )


class LLMClientEndpointsView(SmarterWebHtmlView):
    """
    A deployed LLMClient's endpoints, for a browser, and The Smarter Project, which built it.

    The page is the ``@smarter/llmclient-deployment`` React app, in its public mode, whose data,
    :func:`deployment_page`'s public copy, is in the page, in a ``json_script``. It names no owner, and has
    no api keys. A host that serves no deployed LLMClient is a 404, as it is for the endpoints themselves.
    """

    template_path = "llmclient/endpoints.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{LLMClientEndpointsView.__name__}[{id(self)}]"
        return logging.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The page, for the LLMClient that serves the request's host.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: The page, or a 404 if no deployed LLMClient serves the host.
        :rtype: django.http.HttpResponse
        """
        llmclient: Optional[LLMClient] = get_cached_llmclient_by_request(request=request)
        if llmclient is None or not llmclient.deployed:
            logger.debug(
                "%s.get() no deployed LLMClient serves %s", self.formatted_class_name, request.build_absolute_uri()
            )
            return SmarterHttpResponseNotFound(request=request, error_message="LLMClient not found.")

        page = deployment_page(llmclient).public()
        logger.debug("%s.get() endpoints page for %s", self.formatted_class_name, llmclient)
        context = {
            "deployment": page.to_json(),
            "deployment_root_id": DEPLOYMENT_ROOT_ID,
            "deployment_data_id": DEPLOYMENT_DATA_ID,
            "react_debug_mode": waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
        }
        return render(request=request, template_name=self.template_path, context=context)


def browser_friendly(api_view: Callable[..., HttpResponseBase]) -> Callable[..., HttpResponseBase]:
    """
    Wrap a deployed LLMClient's api view, so that a GET or HEAD receives :class:`LLMClientEndpointsView`.

    Only while the ``enable_llmclient_endpoints_page`` switch is active. Every other request, including a
    GET while it is inactive, goes to the api view. The wrapper keeps the api view's attributes, e.g. ``csrf_exempt``.

    .. code-block:: python

        path("prompt/", browser_friendly(DefaultLLMClientApiView.as_view())),

    :param api_view: The api view, from ``as_view()``.
    :type api_view: Callable[..., django.http.response.HttpResponseBase]
    :returns: The wrapped view.
    :rtype: Callable[..., django.http.response.HttpResponseBase]
    """
    endpoints_view = LLMClientEndpointsView.as_view()

    @wraps(api_view)
    def view(request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        if request.method in BROWSER_METHODS and waffle.switch_is_active(
            SmarterWaffleSwitches.ENABLE_LLMCLIENT_ENDPOINTS_PAGE
        ):
            return endpoints_view(request, *args, **kwargs)
        return api_view(request, *args, **kwargs)

    return view
