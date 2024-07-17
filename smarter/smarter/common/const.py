# pylint: disable=E1101
"""A module containing constants for the OpenAI API."""
import importlib.util
import logging
import os
from abc import ABC
from pathlib import Path
from typing import Dict, List

import hcl2
import openai


logger = logging.getLogger(__name__)

SMARTER_ACCOUNT_NUMBER = "3141-5926-5359"
SMARTER_CUSTOMER_API_SUBDOMAIN = "api"
SMARTER_CUSTOMER_PLATFORM_SUBDOMAIN = "platform"
SMARTER_COMPANY_NAME = "Smarter"
SMARTER_EXAMPLE_CHATBOT_NAME = "example"
SMARTER_CUSTOMER_SUPPORT = "support@smarter.sh"


HERE = os.path.abspath(os.path.dirname(__file__))  # smarter/smarter/common
PROJECT_ROOT = str(Path(HERE).parent)  # smarter/smarter
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)  # smarter
TERRAFORM_ROOT = str(Path(PROJECT_ROOT).parent.parent)  # ./
REPO_ROOT = str(Path(PYTHON_ROOT).parent.parent)  # ./

TERRAFORM_TFVARS = os.path.join(TERRAFORM_ROOT, "terraform.tfvars")
if not os.path.exists(TERRAFORM_TFVARS):
    TERRAFORM_TFVARS = os.path.join(PROJECT_ROOT, "terraform.tfvars")

TFVARS = {}
IS_USING_TFVARS = False

try:
    with open(TERRAFORM_TFVARS, encoding="utf-8") as f:
        TFVARS = hcl2.load(f)
    IS_USING_TFVARS = True
except FileNotFoundError:
    logger.info("No terraform.tfvars file found. Using default values.")


def load_version() -> Dict[str, str]:
    """Stringify the __version__ module."""
    version_file_path = os.path.join(PROJECT_ROOT, "__version__.py")
    spec = importlib.util.spec_from_file_location("__version__", version_file_path)
    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)
    return version_module.__dict__


VERSION = load_version()


# pylint: disable=too-few-public-methods
class SmarterEnvironments:
    """A class representing the fixed set environments for the Smarter API."""

    LOCAL = "local"
    ALPHA = "alpha"
    BETA = "beta"
    NEXT = "next"
    PROD = "prod"
    all = [LOCAL, ALPHA, BETA, NEXT, PROD]
    aws_environments = [ALPHA, BETA, NEXT, PROD]


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


class LLM(ABC):
    """Base class for Large Language Model classes."""

    name = None
    all_models = None
    default_model = None
    default_max_tokens = 2048
    is_default = False
    smarter_plugin_support = False

    def __init__(self) -> None:
        super().__init__()
        self.name = self.__class__.__name__
        if not self.all_models:
            raise NotImplementedError("all_models must be set in the subclass.")
        if not self.default_model:
            raise NotImplementedError("default_model must be set in the subclass.")

    @property
    def presentation_name(self) -> str:
        return self.name.replace("LLM", "") if self.name else "MISSING NAME"

    def __str__(self) -> str:
        return self.name


class LLMAnthropic(LLM):
    """
    Anthropic Large Language Model class.
    https://docs.anthropic.com/en/docs/about-claude/models
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


class LLMCohere(LLM):
    """
    Cohere Large Language Model class.
    https://docs.cohere.com/docs/models
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


class LLMGoogleAIStudio(LLM):
    """
    Google AI Studio Large Language Model class.
    https://ai.google.dev/gemini-api/docs/models/gemini
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


class LLMMistral(LLM):
    """
    Mistral Large Language Model class.
    https://docs.mistral.ai/getting-started/models/
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


class LLMOpenAI(LLM):
    """OpenAI Large Language Model class."""

    GPT3 = "gpt-3.5-turbo"
    GPT4 = "gpt-4"
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


class LLMDefault(LLM):
    """Default Large Language Model class."""

    llm = LLMOpenAI()

    all_models = llm.all_models
    name = llm.name
    is_default = True
    default_model = llm.default_model
    smarter_plugin_support = llm.smarter_plugin_support


class LLMAll:
    """All Large Language Model classes."""

    llm_anthropic = LLMAnthropic()
    llm_cohere = LLMCohere()
    llm_google_ai_studio = LLMGoogleAIStudio()
    llm_mistral = LLMMistral()
    llm_openai = LLMOpenAI()
    llm_default = LLMDefault()

    all: List[LLM] = [
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
    def get_llm_by_name(cls, llm_name: str) -> LLM:
        """Get an LLM object by name."""
        for llm in cls.all:
            if llm.name == llm_name:
                return llm
        raise ValueError(f"Unknown LLM name: {llm_name}")

    @classmethod
    def get_llm_by_model_name(cls, model_name: str) -> LLM:
        """Get an LLM object by model name."""
        for llm in cls.all:
            if model_name in llm.all_models:
                return llm
        raise ValueError(f"Unknown model name: {model_name}")

    @classmethod
    def get_default_llm(cls) -> LLM:
        """Get the default LLM object."""
        for llm in cls.all:
            if llm.is_default:
                return llm
        raise ValueError("No default LLM found.")


VALID_CHAT_COMPLETION_MODELS = LLMAll.all_models


VALID_EMBEDDING_MODELS = [
    "text-embedding-ada-002",
    "text-similarity-*-001",
    "text-search-*-*-001",
    "code-search-*-*-001",
]
