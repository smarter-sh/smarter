"""Test :mod:`smarter.lib.manifest.record_locator`, which turns a record locator into a web console url."""

import uuid
from unittest.mock import patch

from django.urls import NoReverseMatch

from smarter.apps.guardrail.models import Guardrail
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.extension.views import detail_url as extension_detail_url
from smarter.apps.llmtool.models import Extension
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.manifest.record_locator import (
    console_paths,
    console_url,
    parse_record_locator,
    record_locator_prefix,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

HASHED_ID = LLMClient(id=1).hashed_id


class TestRecordLocator(SmarterTestBase):
    """Test parsing record locators, and the web console page of each kind of resource that has one."""

    def test_record_locator_prefix(self):
        """Test that a model's prefix is the one that its record locators start with."""
        self.assertEqual(record_locator_prefix(LLMClient), "llmclient")
        self.assertEqual(LLMClient(id=1).record_locator, f"{record_locator_prefix(LLMClient)}-{HASHED_ID}")

    def test_parse_record_locator(self):
        """Test that a record locator splits at its first hyphen, so that a key_id keeps its own."""
        self.assertEqual(parse_record_locator("llmclient-rMTAwMDAxMwx"), ("llmclient", "rMTAwMDAxMwx"))
        key_id = str(uuid.uuid4())
        self.assertEqual(parse_record_locator(f"smarterauthtoken-{key_id}"), ("smarterauthtoken", key_id))
        for not_a_record_locator in ("", "llmclient", "llmclient-", "-rMTAwMDAxMwx"):
            with self.subTest(record_locator=not_a_record_locator):
                with self.assertRaises(ValueError):
                    parse_record_locator(not_a_record_locator)

    def test_console_url(self):
        """Test that an LLMClient's record locator leads to its workbench, and a Guardrail's to its page."""
        self.assertEqual(console_url(f"llmclient-{HASHED_ID}"), f"/workbench/llm-clients/{HASHED_ID}/prompt/")
        self.assertEqual(console_url(Guardrail(id=1).record_locator), f"/guardrail/guardrails/{HASHED_ID}/")

    def test_every_page_reverses(self):
        """Test that every kind's page has a url, except those that this platform turns off."""
        for prefix, path in console_paths().items():
            if prefix in ("extension", "smarterauthtoken"):
                continue
            with self.subTest(prefix=prefix):
                try:
                    url = path(HASHED_ID)
                except NoReverseMatch:
                    # e.g. the Proxy and Vectorstore pages, while their waffle switches are off.
                    continue
                self.assertIn(HASHED_ID, url)

    def test_every_prefix_is_a_record_locator_prefix(self):
        """Test that each prefix is that of a model that has record locators."""
        self.assertIn("pluginmeta", console_paths())
        self.assertIn("vectorstoremeta", console_paths())
        self.assertIn("llmclientcustomdomain", console_paths())
        for prefix in console_paths():
            self.assertEqual(prefix, prefix.lower())
            self.assertNotIn("-", prefix)

    def test_an_api_key(self):
        """Test that an api key's record locator, which ends with its key_id, leads to its page."""
        key_id = uuid.uuid4()
        self.assertEqual(SmarterAuthToken(key_id=key_id).record_locator, f"smarterauthtoken-{key_id}")
        self.assertEqual(console_url(f"smarterauthtoken-{key_id}"), f"/authtoken/{key_id}/")

    def test_an_extension(self):
        """Test that an Extension's record locator leads to its page, by its slug, and a missing one to none."""
        extension = Extension.objects.first()
        if extension is not None:
            self.assertEqual(console_url(extension.record_locator), extension_detail_url(extension.slug))
        self.assertIsNone(console_url(Extension(id=999999999).record_locator))

    def test_no_page(self):
        """Test that a record locator without a page, or that is not one, has no url."""
        self.assertIsNone(console_url(None))
        self.assertIsNone(console_url(""))
        self.assertIsNone(console_url("not a record locator"))
        self.assertIsNone(console_url(f"prompt-{HASHED_ID}"))

    def test_a_page_that_is_turned_off(self):
        """Test that a page that does not reverse, e.g. while its app's urls are off, has no url."""
        with patch("smarter.lib.manifest.record_locator.reverse", side_effect=NoReverseMatch("off")):
            self.assertIsNone(console_url(f"guardrail-{HASHED_ID}"))

    def test_record_locators_round_trip(self):
        """Test that a record locator's hashed id is the model's own, so that the url finds the same row."""
        prefix, hashed_id = parse_record_locator(Guardrail(id=42).record_locator)
        self.assertEqual(prefix, record_locator_prefix(Guardrail))
        self.assertEqual(Guardrail.id_from_hashed_id(hashed_id), 42)
