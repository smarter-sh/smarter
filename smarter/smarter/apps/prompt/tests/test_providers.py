# pylint: disable=W0613,W0718
"""Test chat provider OpenAI."""

from typing import Callable

from smarter.apps.prompt.providers.googleai.classes import GoogleAIChatProvider
from smarter.apps.prompt.providers.googleai.const import (
    PROVIDER_NAME as GOOGLEAI_PROVIDER_NAME,
)
from smarter.apps.prompt.providers.metaai.classes import MetaAIChatProvider
from smarter.apps.prompt.providers.metaai.const import (
    PROVIDER_NAME as METAAI_PROVIDER_NAME,
)
from smarter.apps.prompt.providers.openai.classes import (
    PROVIDER_NAME as OPENAI_PROVIDER_NAME,
)
from smarter.apps.prompt.providers.openai.classes import (
    OpenAIChatProvider,
)
from smarter.apps.prompt.providers.providers import chat_providers
from smarter.lib.unittest.base_classes import SmarterTestBase

from .classes import ProviderBaseClass


class TestChatProviders(SmarterTestBase):
    """Test chat provider base class."""

    def verify_providers(self):
        """Test chat providers."""
        self.assertIsInstance(chat_providers.openai, OpenAIChatProvider)
        self.assertIsInstance(chat_providers.googleai, GoogleAIChatProvider)
        self.assertIsInstance(chat_providers.metaai, MetaAIChatProvider)

    def verify_providers_name_readonly(self):
        """Test that chat provider names are read-only."""
        with self.assertRaises(AttributeError):
            chat_providers.openai.provider = "new_name"

        with self.assertRaises(AttributeError):
            chat_providers.googleai.provider = "new_name"

        with self.assertRaises(AttributeError):
            chat_providers.metaai.provider = "new_name"

    def verify_providers_get_handler(self):
        """Test provider get_handler()."""

        handler = chat_providers.get_handler(provider=chat_providers.openai.provider)
        self.assertIsInstance(handler, Callable)

        handler = chat_providers.get_handler(provider=chat_providers.googleai.provider)
        self.assertIsInstance(handler, Callable)

        handler = chat_providers.get_handler(provider=chat_providers.metaai.provider)
        self.assertIsInstance(handler, Callable)

        handler = chat_providers.get_handler()
        self.assertIsInstance(handler, Callable)

    def verify_providers_all(self):
        """Test provider all()."""
        this_all = [OPENAI_PROVIDER_NAME, GOOGLEAI_PROVIDER_NAME, METAAI_PROVIDER_NAME]
        self.assertCountEqual(chat_providers.all, this_all)
        self.assertIn(OPENAI_PROVIDER_NAME, chat_providers.all)
        self.assertIn(GOOGLEAI_PROVIDER_NAME, chat_providers.all)
        self.assertIn(METAAI_PROVIDER_NAME, chat_providers.all)


class TestProviderGoogleai(ProviderBaseClass):
    """Test chat provider Google AI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = chat_providers.googleai.provider


class TestProviderMetaai(ProviderBaseClass):
    """Test chat provider Meta AI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = chat_providers.metaai.provider


class TestProviderOpenai(ProviderBaseClass):
    """Test chat provider OpenAI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider = chat_providers.openai.provider
