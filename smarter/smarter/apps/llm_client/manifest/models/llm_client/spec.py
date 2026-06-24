"""Smarter API Manifest - Plugin.spec."""

import os
from typing import ClassVar, List, Optional

from pydantic import Field

from smarter.apps.llm_client.manifest.models.llm_client.const import MANIFEST_KIND
from smarter.common.conf import settings_defaults
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


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


class SAMLLMClientSpecConfig(AbstractSAMSpecBase):
    """Smarter API LLMClient Manifest LLMClient.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    subdomain: Optional[str] = Field(
        None,
        description=(
            f"{class_identifier}.subdomain[str]. Optional. The subdomain to use for the llm_client for published public urls. Example: https://<subdomain>.3141-5926-5359.api.example.com"
        ),
    )
    customDomain: Optional[SAMLLMClientCustomDomain] = Field(
        None,
        description=(
            f"{class_identifier}.custom_domain[str]. Optional. The custom domain to use for the llm_client. Example: example.com"
        ),
    )
    deployed: bool = Field(
        default=False,
        description=f"{class_identifier}.deployed[bool]. Required. Whether the llm_client is deployed. Deployed means that the llm_client is available for use outside the Smarter Prompt Engineer Workbench. Published llm_clients have their own subdomain, Kubernetes ingress, and TLS/SSL certificate.",
    )
    provider: Optional[str] = Field(
        None,
        description=f"{class_identifier}.provider[str]. Optional. The provider to use for the llm_client.",
    )
    defaultModel: Optional[str] = Field(
        None,
        description=f"{class_identifier}.default_model[str]. Optional. The default model to use for the llm_client. This changes routinely and is currently defaults to {settings_defaults.LLM_DEFAULT_MODEL}",
    )
    defaultSystemRole: Optional[str] = Field(
        None,
        description=f"{class_identifier}.default_system_role[str]. Optional. The default system prompt to use for the llm_client. This defaults to the following value:\n{settings_defaults.LLM_DEFAULT_SYSTEM_ROLE}.\nThe system prompt is the first message in the conversation and is used to set the context for the llm_client. It is important to keep this prompt short, as it is included in the token count for each message. The maximum length of the system prompt is {SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH} characters.",
    )
    defaultTemperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description=f"{class_identifier}.default_temperature[float]. Optional. The default temperature to use for the llm_client. This defaults to {settings_defaults.LLM_DEFAULT_TEMPERATURE}.\nThe temperature is a floating point value between 0 and 1 that controls the randomness of the llm_client's responses. A value of 0 means that the llm_client will always choose the most likely response, while a value of 1 means that the llm_client will choose a random response. Low values work better for information retrieval tasks, while high values work better for creative tasks.",
    )
    defaultMaxTokens: Optional[int] = Field(
        None,
        gt=0,
        description=f"{class_identifier}.default_max_tokens[int]. Optional. The default max tokens to use for the llm_client. This defaults to {settings_defaults.LLM_DEFAULT_MAX_TOKENS}.\nThe max tokens is an integer value that controls the maximum number of tokens in the llm_client's response. The maximum number of tokens is the sum of the tokens in the prompt and the tokens in the response. The maximum number of tokens varies by provider. Refer to vendor documentation as this value routinely changes as new models are released.",
    )

    appName: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_name[str]. Optional. The name of the llm_client. Example: 'Sales Support LLMClient'. This is the name that will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appAssistant: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_assistant[str]. Optional. The assistant name of the llm_client. Example: 'Joe'. This is the fictitious assistant name that will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appWelcomeMessage: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_welcome_message[str]. Optional. The welcome message of the llm_client. Example: 'Welcome to Smarter's sales support llm_client!' The welcome messages will appear as the first assistant message in each message list from the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appExamplePrompts: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.app_example_prompts[list]. Optional. A list of example prompts to add to new prompt sessions. These are intended to be brief, and the list is assumed to include only a few examples. Example: ['How do I get a refund?', 'What is the return policy?']. These are intended to help the user to understand the llm_client's capabilities. These will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appPlaceholder: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_placeholder[str]. Optional. The text placeholder added to the prompt input box for all new prompt sessions. Example: 'ask me anything...'. The place holder will be displayed to users in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appInfoUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_info_url[str]. Optional. The custom info URL of the llm_client. This is a user control button located on the right-hand side of the header of the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appBackgroundImageUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_background_image_url[str]. Optional. The image URL for the background image of the prompt window in the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
    )
    appLogoUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.app_logo_url[str]. Optional. The URL for the llm_client logo. This is future use and is anticipated to be used for meta presentation of this llm_client in UI collections.",
    )
    appFileAttachment: Optional[bool] = Field(
        False,
        description=f"{class_identifier}.app_file_attachment[bool]. Optional. Whether the llm_client supports file attachments. Defaults to False. When set to True, a file attachment button will be displayed in the prompt input box of the Smarter Prompt Engineer Workbench, as well as any production UI that leverages the SmarterChat React.js Component - https://www.npmjs.com/package/@smarter.sh/ui-prompt.",
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
        f"{MANIFEST_KIND}. Plugins are a proprietary extensibility model for tool calling and are not the same as OpenAI plugins. See https://platform.smarter.sh/docs/plugins/ for more information.",
    )
    functions: Optional[List[str]] = Field(
        None,
        description=f"{class_identifier}.functions[list]. Optional. The built-in Smarter Functions to add to the {MANIFEST_KIND}. Example: ['get_current_weather']. These are built-in backing functions written in Python that are fully compatible with OpenAI API-compatible function calling. These are not the same as OpenAI functions. See https://platform.smarter.sh/docs/functions/ for more information.",
    )
    apiKey: Optional[str] = Field(
        None,
        description=f"{class_identifier}.apiKey[str]. Optional. The name of the API key that this llm_client uses for authentication. Example: 'my_api_key'. API keys are only necessary for llm_clients that are not public facing. This is the name of the API key that is used to authenticate the llm_client with the Smarter API. API keys are issued by a Smarter platform administrator and are used to authenticate the llm_client with the Smarter API.",
    )
