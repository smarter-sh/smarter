# pylint: disable=W0221
"""A module containing constants for the OpenAI API."""

import os
from abc import ABC
from typing import List, Optional, Type

import openai
from langchain_anthropic import ChatAnthropic
from langchain_cohere import ChatCohere
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_fireworks import ChatFireworks
from langchain_google_vertexai import ChatVertexAI
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_openai import ChatOpenAI
from langchain_together import ChatTogether
from pydantic import SecretStr

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterLLMDefaults


class LLMVendor(ABC):
    """Base class for Large Language Model classes."""

    # read-only
    _api_key: SecretStr = None
    _name: str = None
    _environment_variable_name: str = None
    _chat_llm_cls: Optional[Type[BaseChatModel]] = None
    _chat_llm: Optional[BaseChatModel] = None

    # writable (set in subclass)
    all_models: List[str] = None
    default_model: str = None
    is_default = False
    smarter_plugin_support = False

    # llm configuration
    _model_name: str = None
    _temperature = SmarterLLMDefaults.TEMPERATURE
    _max_tokens = SmarterLLMDefaults.MAX_TOKENS
    _timeout = SmarterLLMDefaults.TIMEOUT
    _max_retries = SmarterLLMDefaults.MAX_RETRIES

    def __init__(self) -> None:
        super().__init__()
        self._name = self.__class__.__name__
        if not self.all_models:
            raise NotImplementedError("all_models must be set in the subclass.")
        if not self.default_model:
            raise NotImplementedError("default_model must be set in the subclass.")

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
    def api_key(self) -> SecretStr:
        return self._api_key

    @property
    def chat_llm_cls(self) -> Type[BaseChatModel]:
        return self._chat_llm_cls

    @property
    def chat_llm(self) -> BaseChatModel:
        raise NotImplementedError("chat_llm must be implemented in the subclass.")

    @property
    def model_name(self) -> str:
        return self._model_name or self.default_model

    @model_name.setter
    def model_name(self, value: str):
        if value and value not in self.all_models:
            raise ValueError(f"Invalid model_name: {value}. Must be one of: {self.all_models}")
        self._model_name = value

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, value: float):
        if value < 0 or value > 1:
            raise ValueError(f"Invalid temperature: {value}. Must be between 0 and 1.")
        self._temperature = value

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @max_tokens.setter
    def max_tokens(self, value: int):
        if value < 1 or value > SmarterLLMDefaults.MAX_MAX_TOKENS:
            raise ValueError(f"Invalid max_tokens: {value}. Must be between 1 and {SmarterLLMDefaults.MAX_MAX_TOKENS}.")
        self._max_tokens = value

    @property
    def timeout(self) -> int:
        return self._timeout

    @timeout.setter
    def timeout(self, value: int):
        if value < 1:
            raise ValueError(f"Invalid timeout: {value}. Must be greater than 0.")
        self._timeout = value

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @max_retries.setter
    def max_retries(self, value: int):
        if value < 0:
            raise ValueError(f"Invalid max_retries: {value}. Must be greater than or equal to 0.")
        self._max_retries = value

    def configure(
        self,
        api_key: SecretStr,
        model_name: str,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Large Language Model.

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """

        # credentials configuration
        self._api_key = api_key
        if self.environment_variable_name and self.api_key:
            os.environ[self.environment_variable_name] = self.api_key.get_secret_value()

        # llm configuration
        self.model_name = model_name
        self.temperature = temperature or self.temperature
        self.max_tokens = max_tokens or self.max_tokens
        self.timeout = timeout or self.timeout
        self.max_retries = max_retries or self.max_retries

        # destroy any existing chat_llm instance so that lazy loading will re-create it
        # with the new configuration.
        self._chat_llm = None

    def __str__(self) -> str:
        return self.name + " - " + self.model_name + " - " + str(self.api_key.get_secret_value()).left(4)


class LLMVendorAnthropic(LLMVendor):
    """
    Anthropic Large Language Model class.
    https://docs.anthropic.com/en/docs/about-claude/models

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An Anthropic API key is required to use this class.

    Usage:
    vendor = LLMVendors.get_by_name(name="LLMVendorAnthropic")
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
        self._chat_llm_cls = ChatAnthropic
        # https://python.langchain.com/v0.2/docs/integrations/platforms/anthropic/
        self._environment_variable_name = "ANTHROPIC_API_KEY"

    @property
    def chat_llm(self) -> ChatAnthropic:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Anthropic Large Language Model.
        see: https://docs.anthropic.com/en/api/getting-started

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.anthropic_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMVendorCohere(LLMVendor):
    """
    ChatCohere Large Language Model class.
    https://docs.cohere.com/docs/models

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A ChatCohere API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMVendorCohere")
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
        self._chat_llm_cls = ChatCohere
        # https://python.langchain.com/v0.1/docs/integrations/providers/cohere/
        self._environment_variable_name = "COHERE_API_KEY"

    @property
    def chat_llm(self) -> ChatCohere:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Cohere Large Language Model.
        see: https://dashboard.cohere.com/api-keys

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.cohere_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMFireworks(LLMVendor):
    """
    ChatFireworks Large Language Model class.
    https://fireworks.ai/

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A ChatFireworks API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMFireworks")
        vendor.configure(model_name=LLMFireworks.FIRE_FUNCTION_V2)
        response = vendor.chat_llm.generate("Hello, world!")
    """

    FIRE_FUNCTION_V2 = "firefunction-v2"
    all_models = [FIRE_FUNCTION_V2]
    default_model = FIRE_FUNCTION_V2
    smarter_plugin_support = True

    def __init__(self) -> None:
        super().__init__()
        # https://python.langchain.com/v0.2/docs/integrations/providers/fireworks/
        self._chat_llm_cls = ChatFireworks
        self._environment_variable_name = "FIREWORKS_API_KEY"

    @property
    def chat_llm(self) -> ChatFireworks:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Fireworks Large Language Model.
        see: https://fireworks.ai/api-keys

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.fireworks_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMVendorGoogleVertex(LLMVendor):
    """
    Google AI Studio Large Language Model class.
    https://ai.google.dev/gemini-api/docs/models/gemini

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A Google AI Studio API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMVendorGoogleVertex")
        vendor.configure(model_name=LLMVendorGoogleVertex.GEMINI_1_5_PRO)
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
        self._chat_llm_cls = ChatVertexAI

    @property
    def chat_llm(self) -> ChatVertexAI:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Google VertexAI Large Language Model.
        see: https://aistudio.google.com/app/apikey

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.google_ai_studio_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMVendorMistral(LLMVendor):
    """
    Mistral Large Language Model class.
    https://docs.mistral.ai/getting-started/models/

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    A MistralAI API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMVendorMistral")
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
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Mistral Large Language Model.
        see: https://console.mistral.ai/api-keys/

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.mistral_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMVendorOpenAI(LLMVendor):
    """
    OpenAI Large Language Model class.

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An OpenAI API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMVendorOpenAI")
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
    def chat_llm(self) -> ChatOpenAI:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def __init__(self) -> None:
        super().__init__()
        # https://python.langchain.com/v0.2/docs/integrations/chat/mistralai/
        self._chat_llm_cls = ChatOpenAI
        self._environment_variable_name = "OPENAI_API_KEY"

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the OpenAI Large Language Model.
        see: https://platform.openai.com/api-keys

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.openai_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMTogether(LLMVendor):
    """
    TogetherAI Large Language Model class.

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An Together API key is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMTogether")
        vendor.configure(model_name=LLMTogether.GPT3)
        response = vendor.chat_llm.generate("Hello, world!")
    """

    LLAMA_3 = "meta-llama/Llama-3-70b-chat-hf"

    all_models = [LLAMA_3]
    default_model = LLAMA_3

    def __init__(self) -> None:
        super().__init__()
        self._chat_llm_cls = ChatTogether

    @property
    def chat_llm(self) -> ChatTogether:
        if not self._chat_llm:
            self._chat_llm = self._chat_llm_cls(
                api_key=self.api_key.get_secret_value(),
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )

        return self._chat_llm

    def configure(
        self,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs,
    ) -> None:
        """
        Configure the Together Large Language Model.

        args:
            model_name (str): The name of the model to use.
            temperature (float): The temperature to use for the model.
            max_tokens (int): The maximum number of tokens for requests.
            timeout (int): The timeout in seconds for the request.
            max_retries (int): The maximum number of retries for the request.
        """
        super().configure(
            api_key=smarter_settings.togetherai_api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )


class LLMDefault(LLMVendor):
    """
    Default Large Language Model class.

    This is a private class. Do not import this class directly.
    Instead, you should use LLMVendors() to create an instance.

    An API key for the default vendor is required to use this class.

    usage:
        vendor = LLMVendors.get_by_name(name="LLMDefault")
        response = vendor.chat_llm.generate("Hello, world!")
    """

    llm = LLMVendorOpenAI()

    all_models = llm.all_models
    name = llm.name
    is_default = True
    default_model = llm.default_model
    smarter_plugin_support = llm.smarter_plugin_support


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
    llm_fireworks = LLMFireworks()
    llm_google_ai_studio = LLMVendorGoogleVertex()
    llm_mistral = LLMVendorMistral()
    llm_openai = LLMVendorOpenAI()
    llm_default = LLMDefault()

    all: List[LLMVendor] = [
        llm_anthropic,
        llm_cohere,
        llm_fireworks,
        llm_google_ai_studio,
        llm_mistral,
        llm_openai,
        llm_default,
    ]

    all_models = (
        llm_anthropic.all_models
        + llm_cohere.all_models
        + llm_fireworks.all_models
        + llm_google_ai_studio.all_models
        + llm_mistral.all_models
        + llm_openai.all_models
    )

    # pylint: disable=E1133
    all_llm_vendors = [llm.name for llm in all]

    @classmethod
    def get_by_name(cls, name: str) -> LLMVendor:
        """Get an LLMVendor object by name."""
        for llm in cls.all:
            if llm.name == name:
                return llm
        raise ValueError(f"Unknown LLMVendor name: {name}")

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


# singleton instance
llm_vendors = LLMVendors()

###############################################################################
# Legacy Constants. All of these are deprecated and should not be used.
###############################################################################
VALID_CHAT_COMPLETION_MODELS = LLMVendors.all_models


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
