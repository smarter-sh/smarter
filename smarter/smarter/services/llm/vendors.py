"""A module containing constants for the OpenAI API."""

import os
from abc import ABC, abstractmethod
from typing import List, Optional, Type

import openai
from langchain_anthropic.llms import AnthropicLLM
from langchain_cohere.llms import Cohere
from langchain_core.language_models.llms import BaseLLM
from langchain_google_genai import GoogleGenerativeAI
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_openai import OpenAI

from smarter.common.conf import settings as smarter_settings


class LLMVendor(ABC):
    """Base class for Large Language Model classes."""

    _api_key: str = None
    _name: str = None
    _environment_variable_name: str = None
    _chat_llm_cls: Optional[Type[BaseLLM]] = None
    _chat_llm: Optional[BaseLLM] = None
    _model_name: str = None
    all_models: List[str] = None
    default_model: str = None
    default_max_tokens = 2048
    is_default = False
    smarter_plugin_support = False

    def __init__(self) -> None:
        super().__init__()
        self._name = self.__class__.__name__
        if not self.all_models:
            raise NotImplementedError("all_models must be set in the subclass.")
        if not self.default_model:
            raise NotImplementedError("default_model must be set in the subclass.")

    @abstractmethod
    def configure(self, model_name: str = None, **kwargs) -> None:
        """Configure the Large Language Model."""
        raise NotImplementedError()

    def configure_environment_variable(self):
        if self.environment_variable_name and self.api_key:
            os.environ[self.environment_variable_name] = self.api_key

    @property
    def name(self) -> str:
        return self._name

    @property
    def environment_variable_name(self) -> str:
        return self._environment_variable_name

    @property
    def presentation_name(self) -> str:
        return self.name.replace("LLMVendor", "") if self.name else "MISSING NAME"

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def chat_llm_cls(self) -> Type[BaseLLM]:
        return self._chat_llm_cls

    @property
    def chat_llm(self) -> BaseLLM:
        raise NotImplementedError("chat_llm must be implemented in the subclass.")

    @property
    def model_name(self) -> str:
        return self._model_name or self.default_model

    @model_name.setter
    def model_name(self, value: str):
        if value and value not in self.all_models:
            raise ValueError(f"Invalid model_name: {value}. Must be one of: {self.all_models}")
        self._model_name = value

    def __str__(self) -> str:
        return self.name


class LLMVendorAnthropic(LLMVendor):
    """
    Anthropic Large Language Model class.
    https://docs.anthropic.com/en/docs/about-claude/models

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An Anthropic API key is required to use this class.

    Usage:
    vendor = LLMVendors.get_by_name(llm_name="LLMVendorAnthropic")
    vendor.configure(model_name=LLMVendorAnthropic.CLAUDE_3_5_SONNET)
    response = vendor.chat_llm.generate("Hello, world!")
    """

    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"

    all_models = [
        CLAUDE_3_5_SONNET,
        CLAUDE_3_OPUS,
        CLAUDE_3_SONNET,
        CLAUDE_3_HAIKU,
    ]
    default_model = CLAUDE_3_5_SONNET
    smarter_plugin_support = True

    def __init__(self) -> None:
        super().__init__()
        self._chat_llm_cls = AnthropicLLM
        # https://python.langchain.com/v0.2/docs/integrations/platforms/anthropic/
        self._environment_variable_name = "ANTHROPIC_API_KEY"

    @property
    def chat_llm(self) -> AnthropicLLM:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(anthropic_api_key=self.api_key, model_name=self.model_name)
        return self._chat_llm

    def configure(self, model_name: str = None, **kwargs) -> None:
        """
        Configure the Anthropic Large Language Model.
        args:
            model_name (str): The name of the model to use.
        """
        self.model_name = model_name
        # - https://docs.anthropic.com/en/api/getting-started
        self._api_key = smarter_settings.anthropic_api_key
        self.configure_environment_variable()


class LLMVendorCohere(LLMVendor):
    """
    Cohere Large Language Model class.
    https://docs.cohere.com/docs/models

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A Cohere API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(llm_name="LLMVendorCohere")
        vendor.configure(model_name=LLMVendorCohere.COMMAND_R_PLUS)
        response = vendor.chat_llm.generate("Hello, world!")
    """

    COMMAND_R_PLUS = "command-r-plus"
    COMMAND_R = "command-r"
    COMMAND = "command"
    COMMAND_NIGHTLY = "command-nightly"
    COMMAND_LIGHT = "command-light"
    COMMAND_LIGHT_NIGHTLY = "command-light-nightly"

    all_models = [
        COMMAND_R_PLUS,
        COMMAND_R,
        COMMAND,
        COMMAND_NIGHTLY,
        COMMAND_LIGHT,
        COMMAND_LIGHT_NIGHTLY,
    ]
    default_model = COMMAND_R_PLUS
    smarter_plugin_support = True

    def __init__(self) -> None:
        super().__init__()
        self._chat_llm_cls = Cohere
        # https://python.langchain.com/v0.1/docs/integrations/providers/cohere/
        self._environment_variable_name = "COHERE_API_KEY"

    @property
    def chat_llm(self) -> Cohere:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(cohere_api_key=self.api_key, model=self.model_name)
        return self._chat_llm

    def configure(self, model_name: str = None, **kwargs) -> None:
        self.model_name = model_name
        # - https://dashboard.cohere.com/api-keys
        self._api_key = smarter_settings.cohere_api_key
        self.configure_environment_variable()


class LLMVendorGoogleAIStudio(LLMVendor):
    """
    Google AI Studio Large Language Model class.
    https://ai.google.dev/gemini-api/docs/models/gemini

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A Google AI Studio API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(llm_name="LLMVendorGoogleAIStudio")
        vendor.configure(model_name=LLMVendorGoogleAIStudio.GEMINI_1_5_PRO)
        response = vendor.chat_llm.generate("Hello, world!")
    """

    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1__0_PRO = "gemini-1.0-pro"
    GEMINI_PRO_VISION = "gemini-pro-vision"
    TEXT_EMBEDDING = "text-embedding-004"
    AQA = "aqa"

    all_models = [
        GEMINI_1_5_PRO,
        GEMINI_1_5_FLASH,
        GEMINI_1__0_PRO,
        GEMINI_PRO_VISION,
        TEXT_EMBEDDING,
        AQA,
    ]
    default_model = GEMINI_1_5_PRO
    smarter_plugin_support = True

    def __init__(self) -> None:
        super().__init__()

        # https://python.langchain.com/v0.2/docs/integrations/llms/google_ai/
        self._chat_llm_cls = GoogleGenerativeAI

    @property
    def chat_llm(self) -> GoogleGenerativeAI:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(google_api_key=self.api_key, model=self.model_name)
        return self._chat_llm

    def configure(self, model_name: str = None, **kwargs) -> None:
        self.model_name = model_name
        # - https://aistudio.google.com/app/apikey
        self._api_key = smarter_settings.google_ai_studio_api_key


class LLMVendorMistral(LLMVendor):
    """
    Mistral Large Language Model class.
    https://docs.mistral.ai/getting-started/models/

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A MistralAI API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(llm_name="LLMVendorMistral")
        vendor.configure(model_name=LLMVendorMistral.MISTRAL_7B)
        response = vendor.chat_llm.generate("Hello, world!")
    """

    MISTRAL_7B = "open-mistral-7b"
    MISTRAL_8X7B = "open-mixtral-8x7b"
    MISTRAL_8X22B = "open-mixtral-8x22"
    MISTRAL_SMALL = "mistral-small-latest"
    MISTRAL_LARGE = "mistral-large-latest"
    MISTRAL_EMBEDDINGS = "mistral-embed"
    CODESTRAL = "codestral-latest"
    CODESTRAL_MAMBA = "codestral-mamba-latest"

    all_models = [
        MISTRAL_7B,
        MISTRAL_8X7B,
        MISTRAL_8X22B,
        MISTRAL_SMALL,
        MISTRAL_LARGE,
        MISTRAL_EMBEDDINGS,
        CODESTRAL,
        CODESTRAL_MAMBA,
    ]
    default_model = MISTRAL_7B
    smarter_plugin_support = True

    def __init__(self) -> None:
        super().__init__()
        # https://python.langchain.com/v0.2/docs/integrations/chat/mistralai/
        self._chat_llm_cls = ChatMistralAI

        self._environment_variable_name = "MISTRAL_API_KEY"

    @property
    def chat_llm(self) -> ChatMistralAI:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(api_key=self.api_key, model_name=self.model_name)
        return self._chat_llm

    def configure(self, model_name: str = None, **kwargs) -> None:
        self.model_name = model_name
        # - https://console.mistral.ai/api-keys/
        self._api_key = smarter_settings.mistral_api_key
        self.configure_environment_variable()


class LLMVendorOpenAI(LLMVendor):
    """
    OpenAI Large Language Model class.

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An OpenAI API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(llm_name="LLMVendorOpenAI")
        vendor.configure(model_name=LLMVendorOpenAI.GPT3)
        response = vendor.chat_llm.generate("Hello, world!")
    """

    GPT4_TURBO = "gpt-4-turbo"
    GPT4_32K = "gpt-4-32k"
    GPT4_1106_PREVIEW = "gpt-4-1106-preview"
    GPT4_0613 = "gpt-4-0613"
    GPT4_32K_0613 = "gpt-4-32k-0613"
    GPT3_5_TURBO = "gpt-3.5-turbo"
    GPT3_5_TURBO_0613 = "gpt-3.5-turbo-0613"
    GPT3_5_TURBO_16K = "gpt-3.5-turbo-16k"
    GPT3_5_TURBO_16K_0613 = "gpt-3.5-turbo-16k-0613"
    GPT3_5_TURBO_1106 = "gpt-3.5-turbo-1106"
    GPT3_5_TURBO_INSTRUCT = "gpt-3.5-turbo-instruct"

    # shorthand
    GPT3 = GPT3_5_TURBO
    GPT4 = GPT4_TURBO

    all_models = [
        GPT3,
        GPT4,
        GPT4_TURBO,
        GPT4_32K,
        GPT4_1106_PREVIEW,
        GPT4_0613,
        GPT4_32K_0613,
        GPT3_5_TURBO,
        GPT3_5_TURBO_0613,
        GPT3_5_TURBO_16K,
        GPT3_5_TURBO_16K_0613,
        GPT3_5_TURBO_1106,
        GPT3_5_TURBO_INSTRUCT,
    ]
    default_model = GPT3
    smarter_plugin_support = True

    @property
    def chat_llm(self) -> OpenAI:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(api_key=self.api_key, model=self.model_name)
        return self._chat_llm

    def __init__(self) -> None:
        super().__init__()
        # https://python.langchain.com/v0.2/docs/integrations/chat/mistralai/
        self._chat_llm_cls = OpenAI
        self._environment_variable_name = "OPENAI_API_KEY"

    def configure(self, model_name: str = None, **kwargs) -> None:
        self.model_name = model_name
        # - https://platform.openai.com/api-keys
        self._api_key = smarter_settings.openai_api_key
        self.configure_environment_variable()


class LLMDefault(LLMVendor):
    """
    Default Large Language Model class.

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An API key for the default vendor is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(llm_name="LLMDefault")
        response = vendor.chat_llm.generate("Hello, world!")
    """

    llm = LLMVendorOpenAI()

    all_models = llm.all_models
    name = llm.name
    is_default = True
    default_model = llm.default_model
    smarter_plugin_support = llm.smarter_plugin_support

    def configure(self, model_name: str = None, **kwargs) -> None:
        """
        this is a no-op since the configuration is done by the actual LLMVendor
        instance that is being used as the default.
        """


class LLMVendors:
    """
    All registered Large Language Model classes. Use this
    helper class to create an instance of any LLMVendor class,
    by name or by model name.

    usage:
        llm = LLMVendors.get_default_llm()
        response = llm.chat_llm.generate("Hello, world!")
    """

    llm_anthropic = LLMVendorAnthropic()
    llm_cohere = LLMVendorCohere()
    llm_google_ai_studio = LLMVendorGoogleAIStudio()
    llm_mistral = LLMVendorMistral()
    llm_openai = LLMVendorOpenAI()
    llm_default = LLMDefault()

    all: List[LLMVendor] = [
        llm_anthropic,
        llm_cohere,
        llm_google_ai_studio,
        llm_mistral,
        llm_openai,
        llm_default,
    ]

    all_models = (
        llm_anthropic.all_models
        + llm_cohere.all_models
        + llm_google_ai_studio.all_models
        + llm_mistral.all_models
        + llm_openai.all_models
    )

    # pylint: disable=E1133
    all_llm_vendors = [llm.name for llm in all]

    @classmethod
    def get_by_name(cls, llm_name: str) -> LLMVendor:
        """Get an LLMVendor object by name."""
        for llm in cls.all:
            if llm.name == llm_name:
                return llm
        raise ValueError(f"Unknown LLMVendor name: {llm_name}")

    @classmethod
    def get_llm_by_model_name(cls, model_name: str) -> LLMVendor:
        """Get an LLMVendor object by model name."""
        for llm in cls.all:
            if model_name in llm.all_models:
                return llm
        raise ValueError(f"Unknown model name: {model_name}")

    @classmethod
    def get_default_llm(cls) -> LLMVendor:
        """Get the default LLMVendor object."""
        for llm in cls.all:
            if llm.is_default:
                return llm
        raise ValueError("No default LLMVendor found.")


VALID_CHAT_COMPLETION_MODELS = LLMVendors.all_models


VALID_EMBEDDING_MODELS = [
    "text-embedding-ada-002",
    "text-similarity-*-001",
    "text-search-*-*-001",
    "code-search-*-*-001",
]


# pylint: disable=too-few-public-methods
class OpenAIObjectTypes:
    """V1 API Object Types (replace OpeanAIEndPoint)"""

    Embedding = "embedding"
    ChatCompletion = "chat.completion"
    Moderation = "moderation"
    Image = "image"
    Audio = "audio"
    Models = "models"
    all_object_types = [Embedding, ChatCompletion, Moderation, Image, Audio, Models]


# pylint: disable=too-few-public-methods
class OpenAIEndPoint:
    """
    A class representing an endpoint for the OpenAI API.

    Attributes:
        api_key (str): The API key to use for authentication.
        endpoint (str): The URL of the OpenAI API endpoint.
    """

    Embedding = openai.Embedding.__name__
    ChatCompletion = "chat/completions"
    Moderation = openai.Moderation.__name__
    Image = openai.Image.__name__
    Audio = openai.Audio.__name__
    Models = openai.Model.__name__
    all_endpoints = [Embedding, ChatCompletion, Moderation, Image, Audio, Models]


# pylint: disable=too-few-public-methods
class OpenAIMessageKeys:
    """A class representing the keys for a message in the OpenAI API."""

    OPENAI_MESSAGE_ROLE_KEY = "role"
    OPENAI_MESSAGE_CONTENT_KEY = "content"
    OPENAI_USER_MESSAGE_KEY = "user"
    OPENAI_ASSISTANT_MESSAGE_KEY = "assistant"
    OPENAI_SYSTEM_MESSAGE_KEY = "system"
    all = [
        OPENAI_SYSTEM_MESSAGE_KEY,
        OPENAI_USER_MESSAGE_KEY,
        OPENAI_ASSISTANT_MESSAGE_KEY,
    ]


LANGCHAIN_MESSAGE_HISTORY_ROLES = ["user", "assistant"]
