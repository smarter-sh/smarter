# pylint: disable=W0613,W0718
"""Test chat provider OpenAI."""

import unittest
from typing import Callable

from smarter.apps.chat.providers.googleai.classes import GoogleAIChatProvider
from smarter.apps.chat.providers.googleai.const import (
    PROVIDER_NAME as GOOGLEAI_PROVIDER_NAME,
)
from smarter.apps.chat.providers.metaai.classes import MetaAIChatProvider
from smarter.apps.chat.providers.metaai.const import (
    PROVIDER_NAME as METAAI_PROVIDER_NAME,
)
from smarter.apps.chat.providers.openai.classes import OpenAIChatProvider
from smarter.apps.chat.providers.openai.const import (
    PROVIDER_NAME as OPENAI_PROVIDER_NAME,
)
from smarter.apps.chat.providers.providers import chat_providers

from .classes import ProviderBaseClass


class TestChatProviders(unittest.TestCase):
    """Test chat provider base class."""

    def test_providers(self):
        """Test chat providers."""
        self.assertIsInstance(chat_providers.openai, OpenAIChatProvider)
        self.assertIsInstance(chat_providers.googleai, GoogleAIChatProvider)
        self.assertIsInstance(chat_providers.metaai, MetaAIChatProvider)

    def test_providers_name_readonly(self):
        """Test that chat provider names are read-only."""
        with self.assertRaises(AttributeError):
            chat_providers.openai.name = "new_name"

        with self.assertRaises(AttributeError):
            chat_providers.googleai.name = "new_name"

        with self.assertRaises(AttributeError):
            chat_providers.metaai.name = "new_name"

    def test_providers_get_handler(self):
        """Test provider get_handler()."""

        handler = chat_providers.get_handler(chat_providers.openai.name)
        self.assertIsInstance(handler, Callable)

        handler = chat_providers.get_handler(chat_providers.googleai.name)
        self.assertIsInstance(handler, Callable)

        handler = chat_providers.get_handler(chat_providers.metaai.name)
        self.assertIsInstance(handler, Callable)

        handler = chat_providers.get_handler()
        self.assertIsInstance(handler, Callable)

    def test_providers_all(self):
        """Test provider all()."""
        this_all = [OPENAI_PROVIDER_NAME, GOOGLEAI_PROVIDER_NAME, METAAI_PROVIDER_NAME]
        self.assertCountEqual(chat_providers.all, this_all)
        self.assertIn(OPENAI_PROVIDER_NAME, chat_providers.all)
        self.assertIn(GOOGLEAI_PROVIDER_NAME, chat_providers.all)
        self.assertIn(METAAI_PROVIDER_NAME, chat_providers.all)


class TestProviderOpenai(ProviderBaseClass):
    """Test chat provider OpenAI."""

    def setUp(self):
        return self.internal_setup(provider=chat_providers.openai.name)

    def tearDown(self):
        return super().internal_teardown()


class TestProviderGoogleai(ProviderBaseClass):
    """Test chat provider Google AI."""

    def setUp(self):
        return self.internal_setup(provider=chat_providers.googleai.name)

    def tearDown(self):
        return super().internal_teardown()


class TestProviderMetaai(ProviderBaseClass):
    """Test chat provider Meta AI."""

    def setUp(self):
        return self.internal_setup(provider=chat_providers.metaai.name)

    def tearDown(self):
        return super().internal_teardown()
