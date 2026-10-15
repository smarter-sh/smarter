"""Smarter API Manifest - Plugin.spec."""

import os
import re
from typing import ClassVar, List, Optional

from pydantic import Field, field_validator

from smarter.apps.llmclient.manifest.models.llmclient.const import MANIFEST_KIND
from smarter.apps.llmclient.manifest.models.llmclient.styles import (
    SAMLLMClientSpecConfigStyles,
)
from smarter.common.conf import settings_defaults
from smarter.lib.manifest.models import AbstractSAMSpecBase
from smarter.lib.manifest.system_role import (
    SMARTER_MAX_SYSTEM_ROLE_LENGTH,
    warn_if_long_system_role,
)

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
ORIGIN_PATTERN = re.compile(r"^https?://[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*(:\d{1,5})?$")
"""An origin, as browsers send it in the ``Origin`` header: a scheme, a host and an optional port."""


class SAMLLMClientCustomDomain(AbstractSAMSpecBase):
    """Smarter API LLMClient Manifest LLMClient.spec.config.customDomain."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration.customDomain"

    aws_hosted_zone_id: str = Field(
        ...,
        description=(
            f"{class_identifier}.aws_hosted_zone_id[str]. Required. The AWS hosted zone ID for this domain name. Example: Z08678681MEAGNEVHT5I8"
        ),
    )
    domain_name: str = Field(
        ...,
        description=(f"{class_identifier}.domain_name[str]. Required. The domain name. Example: example.com"),
    )


class SAMLLMClientSpecConfigPrompt(AbstractSAMSpecBase):
    """
    Smarter API LLMClient Manifest LLMClient.spec.config.prompt.

    What the LLMClient is and does: its LLM provider, model and system prompt, the text of its chat
    (its name, welcome message, example prompts and placeholder), and where it is published.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration.prompt"

    subdomain: Optional[str] = Field(
        None,
        description=(
            f"{class_identifier}.subdomain[str]. Optional. The subdomain to use for the llmclient for published public urls. Example: https://<subdomain>.3141-5926-5359.api.example.com"
        ),
    )
    customDomain: Optional[SAMLLMClientCustomDomain] = Field(
        None,
        description=(
            f"{class_identifier}.custom_domain[str]. Optional. The custom domain to use for the llmclient. Example: example.com"
        ),
    )
    deployed: bool = Field(
        default=False,
        description=f"{class_identifier}.deployed[bool]. Required. Whether the llmclient is deployed. Deployed means that the llmclient is available for use outside the Smarter Prompt Engineer Workbench. Published llmclients have their own subdomain, Kubernetes ingress, and TLS/SSL certificate.",
    )
    provider: Optional[str] = Field(
        None,
        description=f"{class_identifier}.provider[str]. Optional. The provider to use for the llmclient.",
    )
    defaultModel: Optional[str] = Field(
        None,
        description=f"{class_identifier}.default_model[str]. Optional. The default model to use for the llmclient. This changes routinely and is currently defaults to {settings_defaults.LLM_DEFAULT_MODEL}",
    )
    defaultSystemRole: Optional[str] = Field(
        None,
        max_length=SMARTER_MAX_SYSTEM_ROLE_LENGTH,
        description=f"{class_identifier}.default_system_role[str]. Optional. The default system prompt to use for the llmclient. This defaults to the following value:\n{settings_defaults.LLM_DEFAULT_SYSTEM_ROLE}.\nThe system prompt is the first message in the conversation and is used to set the context for the llmclient. It is sent with every prompt, so its tokens count towards every turn's cost. The maximum length of the system prompt is {SMARTER_MAX_SYSTEM_ROLE_LENGTH} characters.",
    )
    defaultTemperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description=f"{class_identifier}.default_temperature[float]. Optional. The default temperature to use for the llmclient. This defaults to {settings_defaults.LLM_DEFAULT_TEMPERATURE}.\nThe temperature is a floating point value between 0 and 1 that controls the randomness of the llmclient's responses. A value of 0 means that the llmclient will always choose the most likely response, while a value of 1 means that the llmclient will choose a random response. Low values work better for information retrieval tasks, while high values work better for creative tasks.",
    )
    defaultMaxTokens: Optional[int] = Field(
        None,
        gt=0,
        description=f"{class_identifier}.default_max_tokens[int]. Optional. The default max tokens to use for the llmclient. This defaults to {settings_defaults.LLM_DEFAULT_MAX_TOKENS}.\nThe max tokens is an integer value that controls the maximum number of tokens in the llmclient's response. The maximum number of tokens is the sum of the tokens in the prompt and the tokens in the response. The maximum number of tokens varies by provider. Refer to vendor documentation as this value routinely changes as new models are released.",
    )

    appName: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_name[str]. Optional. The name of the llmclient. Example: 'Sales Support LLMClient'. This is the name that will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appAssistant: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_assistant[str]. Optional. The assistant name of the llmclient. Example: 'Joe'. This is the fictitious assistant name that will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appWelcomeMessage: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_welcome_message[str]. Optional. The welcome message of the llmclient. Example: 'Welcome to Smarter's sales support llmclient!' The welcome messages will appear as the first assistant message in each message list from the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appExamplePrompts: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.app_example_prompts[list]. Optional. A list of example prompts to add to new prompt sessions. These are intended to be brief, and the list is assumed to include only a few examples. Example: ['How do I get a refund?', 'What is the return policy?']. These are intended to help the user to understand the llmclient's capabilities. These will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appPlaceholder: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_placeholder[str]. Optional. The text placeholder added to the prompt input box for all new prompt sessions. Example: 'ask me anything...'. The place holder will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appInfoUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_info_url[str]. Optional. The custom info URL of the llmclient. This is a user control button located on the right-hand side of the header of the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appFileAttachment: Optional[bool] = Field(
        False,
        description=f"{class_identifier}.app_file_attachment[bool]. Optional. Whether the llmclient supports file attachments. Defaults to False. When set to True, a file attachment button will be displayed in the prompt input box of the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    allowedOrigins: Optional[List[str]] = Field(
        default_factory=list,
        description=(
            f"{class_identifier}.allowed_origins[list[str]]. Optional. The origins of the web pages that may call "
            "this llmclient from a browser, with the @smarter.sh/ui-chat React component, in addition to those that "
            "the Smarter platform allows. An origin is a scheme, a host and an optional port, without a path or a "
            "wildcard. Example: ['https://www.example.com', 'http://localhost:5173']."
        ),
    )

    @field_validator("defaultSystemRole")
    @classmethod
    def validate_default_system_role(cls, value: Optional[str]) -> Optional[str]:
        """
        Log a warning for a ``defaultSystemRole`` that is unusually long.

        :param value: The system role.
        :type value: Optional[str]
        :returns: The system role, unchanged.
        :rtype: Optional[str]
        """
        if value is None:
            return value
        return warn_if_long_system_role(value, f"{cls.class_identifier}.defaultSystemRole")

    @field_validator("allowedOrigins")
    @classmethod
    def validate_allowed_origins(cls, value: Optional[List[str]]) -> List[str]:
        """
        Validate and normalize ``allowedOrigins``: each is ``http(s)://host[:port]``, lowercased.

        :param value: The origins.
        :type value: Optional[List[str]]
        :returns: The normalized origins, without duplicates, in their order.
        :rtype: List[str]
        :raises ValueError: If an origin has a path, a wildcard, or another scheme.
        """
        origins: List[str] = []
        for origin in value or []:
            normalized = str(origin).strip().lower().rstrip("/")
            if not ORIGIN_PATTERN.match(normalized):
                raise ValueError(
                    f"allowedOrigins: {origin!r} is not an origin. Use a scheme, a host and an optional port, "
                    "e.g. 'https://www.example.com', without a path or a wildcard."
                )
            if normalized not in origins:
                origins.append(normalized)
        return origins


class SAMLLMClientSpecConfig(AbstractSAMSpecBase):
    """
    Smarter API LLMClient Manifest LLMClient.spec.config.

    ``prompt``, which is required, configures the LLMClient, and ``styles``, which is optional, the
    look of its chat.

    Manifests written before the split have their settings directly in ``spec.config``. Apply
    rejects them, with an error that says where each setting belongs now. See
    :meth:`smarter.apps.llmclient.manifest.brokers.llmclient.SAMLLMClientBroker.raise_for_unknown_keys`.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    prompt: SAMLLMClientSpecConfigPrompt = Field(
        ...,
        description=(
            f"{class_identifier}.prompt[object]. Required. The LLMClient's LLM provider, model and system prompt, "
            "the text of its chat, and where it is published."
        ),
    )
    styles: Optional[SAMLLMClientSpecConfigStyles] = Field(
        None,
        description=(
            f"{class_identifier}.styles[object]. Optional. The look of the LLMClient's chat, in the Smarter "
            "workbench and on every page that embeds it: its logo, background image, fonts and colors. See "
            "https://docs.smarter.sh/en/latest/smarter-resources/llmclient/styles.html"
        ),
    )


class SAMLLMClientSpec(AbstractSAMSpecBase):
    """Smarter API LLMClient Manifest LLMClient.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMLLMClientSpecConfig = Field(
        ..., description=f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."
    )
    plugins: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.searchTerms[list]. Optional. The Plugins to add to the "
        f"{MANIFEST_KIND}. Plugins are a proprietary extensibility model for tool calling and are not the same as OpenAI plugins. See https://docs.smarter.sh/plugins/ for more information.",
    )
    extensions: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.extensions[list]. Optional. The slugs of the Extensions whose tools the {MANIFEST_KIND} offers the LLM. Example: ['weather', 'calculator']. Extensions are Python packages that a platform administrator installs; each must be installed, enabled and available to your account. See https://docs.smarter.sh/ for more information.",
    )
    guardrails: Optional[List[str]] = Field(
        None,
        description=(
            f"{class_identifier}.guardrails[list]. Optional. The names of the Guardrails that protect the "
            f"{MANIFEST_KIND}'s prompts. Example: ['pii_redaction_input', 'prompt_injection_keyword_input']. Each "
            "must be a Guardrail that you own, or that is shared with you, such as Smarter's built-in guardrails. "
            "Input guardrails run on the user's message before it is sent to the LLM, and output guardrails on the "
            "LLM's reply before it is returned to the user, in order of their priority. Experimental."
        ),
    )
    mcpClients: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.mcpClients[list]. Optional. The names of the MCPClients whose MCP servers' tools the {MANIFEST_KIND} offers the LLM. Example: ['deepwiki']. Each must be an MCPClient that you own, or that is shared with you. Experimental.",
    )
    apiKey: Optional[str] = Field(
        None,
        description=f"{class_identifier}.apiKey[str]. Optional. The name of the API key that this llmclient uses for authentication. Example: 'my_api_key'. API keys are only necessary for llmclients that are not public facing. This is the name of the API key that is used to authenticate the llmclient with the Smarter API. API keys are issued by a Smarter platform administrator and are used to authenticate the llmclient with the Smarter API.",
    )
