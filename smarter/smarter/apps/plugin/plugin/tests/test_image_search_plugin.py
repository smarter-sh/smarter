# pylint: disable=too-many-public-methods,protected-access
"""
Unit tests for :py:class:`smarter.apps.plugin.plugin.image_search.ImageSearchPlugin`, and for the.

:py:class:`smarter.apps.plugin.models.PluginDataImageSearch` model that stores its configuration.

The shared fixture is an ImageSearchPlugin, from ``./data/image-search-plugin.yaml``, whose
Brave Search API key is a test Secret. The Brave Image Search API, and the image urls that it
returns, are served by a :class:`FakeWebHost`.

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

import copy
import glob
import os
from typing import Any, Optional
from unittest import mock

from pydantic import ValidationError

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.plugin.manifest.brokers.image_search_plugin import (
    SAMImageSearchPluginBroker,
)
from smarter.apps.plugin.manifest.controller import (
    PLUGIN_MAP,
    PLUGIN_META_CLASS_MAP,
    SAM_MAP,
    PluginController,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.const import (
    BRAVE_IMAGE_SEARCH_URL,
    DEFAULT_API_KEY_SECRET_NAME,
    MANIFEST_KIND,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.model import (
    SAMImageSearchPlugin,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.spec import (
    ImageSearchData,
    ImageSearchFilters,
    ImageSearchParams,
    normalize_country,
    normalize_file_types,
    normalize_search_lang,
)
from smarter.apps.plugin.models import (
    PLUGIN_DATA_MAP,
    PluginDataImageSearch,
    PluginMeta,
)
from smarter.apps.plugin.plugin.image_search import (
    ImageResult,
    ImageSearchPlugin,
    SmarterImageSearchPluginError,
    as_dimension,
    describe_brave_error,
    file_type_of_content_type,
    file_type_of_url,
    is_https_url,
    parse_brave_images,
)
from smarter.apps.plugin.plugin.safe_http import SafeHttpError
from smarter.apps.plugin.serializers import PluginImageSearchSerializer
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json
from smarter.lib.manifest.exceptions import SAMValidationError

from .base_classes import FakeWebHost, PluginTestBase, get_test_data, mock_web_host

HERE = os.path.abspath(os.path.dirname(__file__))
SAMPLE_PLUGINS_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "data", "sample-plugins"))
LLMCLIENTS_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "..", "llmclient", "data", "llm-clients"))
WEATHER_IMAGE_SEARCH_DESCRIPTION = "Searches the web for images"
"""The opening words of the image_search tool's description, which the weather LLMClient's prompt quotes."""
API_KEY_SECRET = "test_brave_image_search_api_key"
API_KEY = "test-brave-api-key"
LOGGER = "smarter.apps.plugin.plugin.image_search"

CAT = "https://images.example.com/cat.png"
DOG = "https://images.example.com/dog.jpg"
PHOTO = "https://images.example.com/photo"
"""An image url without a file extension, whose response is image/jpeg."""
MISSING = "https://images.example.com/missing.png"
"""An image url that responds with HTTP 404."""
HOTLINK = "https://images.example.com/hotlink"
"""An image url without a file extension, whose response is a web page."""


def brave_result(image_url: Optional[str], page_url: str = "https://site.example/page", width: Any = 800) -> dict:
    """Return a Brave Image Search API result."""
    result: dict[str, Any] = {"type": "image_result", "title": "An image", "url": page_url}
    if image_url is not None:
        result["properties"] = {"url": image_url, "placeholder": "https://imgs.search.brave.com/p", "width": width}
    result["thumbnail"] = {"src": "https://imgs.search.brave.com/thumbnail"}
    return result


BRAVE_RESULTS = [
    brave_result(CAT),
    brave_result("http://insecure.example.com/bird.png"),
    brave_result(CAT),
    brave_result("https://images.example.com/tiny.png", width=50),
    brave_result("https://images.example.com/blocked.png", page_url="https://blocked.example/page"),
    brave_result("https://images.example.com/animation.gif"),
    brave_result(MISSING),
    brave_result(HOTLINK),
    brave_result(None),
    brave_result("https://images.example.com/unknown-size.png", width=None),
    brave_result(DOG),
    brave_result(PHOTO),
]
"""
A Brave response.

With the fixture's filters (jpg|png, minWidth 100, blocked.example) and url
validation, the plugin returns, in order: CAT, DOG and PHOTO. unknown-size.png is skipped,
since its width is unknown and the fixture has a minWidth.
"""


def web(results: Optional[list] = None, status_code: int = 200) -> FakeWebHost:
    """Serve the Brave Image Search API, and the image urls."""
    host = FakeWebHost()
    host.add_json(
        BRAVE_IMAGE_SEARCH_URL,
        {"type": "images", "results": BRAVE_RESULTS if results is None else results},
        status_code,
    )
    for url, content_type in ((CAT, "image/png"), (DOG, "image/jpeg"), (PHOTO, "image/jpeg; charset=binary")):
        host.add(url, b"", 200, {"Content-Type": content_type})
    host.add(HOTLINK, b"<html></html>", 200, {"Content-Type": "text/html"})
    for url in ("https://images.example.com/tiny.png", "https://images.example.com/blocked.png"):
        host.add(url, b"", 200, {"Content-Type": "image/png"})
    return host


class TestImageSearchPlugin(PluginTestBase):
    """Test ImageSearchPlugin, using a shared ImageSearchPlugin fixture."""

    sql_fixtures = False
    api_fixtures = False

    image_search_yaml: dict
    image_search_plugin: ImageSearchPlugin
    api_key_secret = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.image_search_yaml = get_test_data("image-search-plugin.yaml")
        cls.api_key_secret = secret_factory(user_profile=cls.user_profile, name=API_KEY_SECRET, value=API_KEY)
        cls.image_search_plugin = ImageSearchPlugin(
            manifest=cls.image_search_manifest("test_image_search_plugin"), user_profile=cls.user_profile
        )

    @classmethod
    def tearDownClass(cls):
        if cls.api_key_secret is not None:
            cls.api_key_secret.delete()
        super().tearDownClass()

    @classmethod
    def image_search_manifest_dict(cls, name: str, **image_search_data) -> dict[str, Any]:
        """Return an ImageSearchPlugin manifest dict, optionally replacing its imageSearchData fields."""
        data = copy.deepcopy(cls.image_search_yaml)
        data["metadata"]["name"] = name
        for key, value in image_search_data.items():
            if value is None:
                data["spec"]["imageSearchData"].pop(key, None)
            else:
                data["spec"]["imageSearchData"][key] = value
        return data

    @classmethod
    def image_search_manifest(cls, name: str, **kwargs) -> SAMImageSearchPlugin:
        """Return an ImageSearchPlugin Pydantic manifest."""
        return SAMImageSearchPlugin(**cls.image_search_manifest_dict(name, **kwargs))

    def load(self) -> ImageSearchPlugin:
        """Return a fresh instance of the shared plugin, loaded from the database."""
        return ImageSearchPlugin(plugin_id=self.image_search_plugin.id, user_profile=self.user_profile)

    def new_plugin(self, name: str, **image_search_data) -> ImageSearchPlugin:
        """Create a throwaway plugin, which is deleted when the test ends."""
        plugin = ImageSearchPlugin(
            manifest=self.image_search_manifest(name, **image_search_data), user_profile=self.user_profile
        )
        self.addCleanup(self.delete_plugin_by_id, plugin.id)
        return plugin

    def call(self, function_args: Any, plugin: Optional[ImageSearchPlugin] = None, host: Optional[FakeWebHost] = None):
        """Run a tool call on a fake Brave Image Search API and a fake web."""
        with mock_web_host(host or web()) as fake:
            retval = (plugin or self.load()).tool_call_fetch_plugin_response(function_args)
        return retval, fake

    @staticmethod
    def brave_calls(fake: FakeWebHost) -> list[dict[str, Any]]:
        """Return the requests that were made to the Brave Image Search API."""
        return [call for call in fake.calls if call["url"] == BRAVE_IMAGE_SEARCH_URL]

    # =========================================================================
    # registration and configuration
    # =========================================================================
    def test_000_fixtures(self):
        """Test the class fixtures themselves."""
        self.assertTrue(self.image_search_plugin.ready)
        self.assertTrue(PluginMeta.objects.filter(id=self.image_search_plugin.id, plugin_class="imagesearch").exists())
        self.assertTrue(PluginDataImageSearch.objects.filter(plugin_id=self.image_search_plugin.id).exists())

    def test_registration(self):
        """Test that ImageSearchPlugin is registered with the plugin controller, data map and CLI brokers."""
        self.assertIs(ImageSearchPlugin.SAMPluginType, SAMImageSearchPlugin)
        self.assertEqual(self.image_search_plugin.kind, MANIFEST_KIND)
        self.assertEqual(MANIFEST_KIND, "ImageSearchPlugin")
        self.assertIs(PLUGIN_MAP[SAMKinds.IMAGE_SEARCH_PLUGIN.value], ImageSearchPlugin)
        self.assertIs(PLUGIN_META_CLASS_MAP["imagesearch"], ImageSearchPlugin)
        self.assertIs(SAM_MAP[SAMKinds.IMAGE_SEARCH_PLUGIN.value], SAMImageSearchPlugin)
        self.assertIs(PLUGIN_DATA_MAP[SAMKinds.IMAGE_SEARCH_PLUGIN.value], PluginDataImageSearch)
        self.assertIs(Brokers.get_broker(SAMKinds.IMAGE_SEARCH_PLUGIN.value), SAMImageSearchPluginBroker)
        self.assertIn(SAMKinds.IMAGE_SEARCH_PLUGIN, SAMKinds.all_plugins())
        plugin = self.load()
        self.assertIs(plugin.plugin_data_class, PluginDataImageSearch)
        self.assertIs(plugin.plugin_data_serializer_class, PluginImageSearchSerializer)
        self.assertIsInstance(plugin.plugin_data_serializer, PluginImageSearchSerializer)
        self.assertEqual(plugin.plugin_meta.kind, SAMKinds.IMAGE_SEARCH_PLUGIN)  # type: ignore[union-attr]

    def test_plugin_controller(self):
        """Test that the plugin controller instantiates an ImageSearchPlugin."""
        plugin_meta = PluginMeta.objects.get(id=self.image_search_plugin.id)
        controller = PluginController(user_profile=self.user_profile, plugin_meta=plugin_meta)
        self.assertIsInstance(controller.plugin, ImageSearchPlugin)
        controller = PluginController(user_profile=self.user_profile, manifest=self.image_search_manifest("x"))
        self.assertEqual(controller.plugin_class, "imagesearch")

    def test_plugin_data(self):
        """Test that the manifest is stored in the plugin data, and becomes Brave's query parameters."""
        plugin_data = self.load().plugin_data
        self.assertIsInstance(plugin_data, PluginDataImageSearch)
        self.assertEqual(plugin_data.api_key_secret_name, API_KEY_SECRET)  # type: ignore[union-attr]
        self.assertEqual(
            plugin_data.search_params("kittens"),  # type: ignore[union-attr]
            {
                "q": "kittens cartoon",
                "count": 3,
                "country": "US",
                "search_lang": "en",
                "safesearch": "strict",
                "spellcheck": "false",
            },
        )
        self.assertEqual(plugin_data.search_params("kittens", count=50)["count"], 3)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.search_params("kittens", count=1)["count"], 1)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.file_types, ["jpg", "png"])  # type: ignore[union-attr]
        self.assertEqual(plugin_data.blocked_domains, ["blocked.example"])  # type: ignore[union-attr]
        self.assertEqual(plugin_data.return_data_keys, [])  # type: ignore[union-attr]
        self.assertNotIn(API_KEY, json.dumps(plugin_data.sanitized_return_data()))  # type: ignore[union-attr]
        self.assertTrue(plugin_data.validate())  # type: ignore[union-attr]
        self.assertEqual(
            PluginDataImageSearch.get_cached_data_by_plugin(self.image_search_plugin.plugin_meta, invalidate=True),  # type: ignore[arg-type]
            plugin_data,
        )

    def test_plugin_data_validate(self):
        """Test that invalid plugin data is rejected."""
        plugin_data = self.load().plugin_data
        for field, value in (
            ("count", 21),
            ("min_width", 0),
            ("timeout", 0),
            ("cache_ttl", -1),
            ("safesearch", "moderate"),
            ("country", "usa"),
            ("search_lang", "english"),
            ("file_type", "jpg|tiff"),
            ("blocked_domains", ["not a domain"]),
            ("api_key_secret_name", " "),
        ):
            data = copy.copy(plugin_data)
            setattr(data, field, value)
            with self.assertRaises(SmarterValueError, msg=field):
                data.validate()  # type: ignore[union-attr]

    def test_plugin_data_save_rejects_invalid_domains(self):
        """Test that saving plugin data with an invalid domain raises."""
        data = copy.copy(self.load().plugin_data)
        data.allowed_domains = ["not a domain"]  # type: ignore[union-attr]
        with self.assertRaises(SmarterValueError):
            data.save()  # type: ignore[union-attr]

    def test_manifest_round_trip(self):
        """Test that the plugin serializes to a manifest equal to the one it was created from."""
        plugin = self.load()
        manifest = plugin.manifest
        self.assertIsInstance(manifest, SAMImageSearchPlugin)
        data = manifest.spec.imageSearchData  # type: ignore[union-attr]
        self.assertEqual(data, self.image_search_manifest("x").spec.imageSearchData)
        self.assertNotIn(API_KEY, json.dumps(plugin.to_json()))
        with self.assertRaises(Exception):
            plugin.to_json(version="v2")

    def test_example_manifest(self):
        """Test that the example manifest is valid."""
        manifest = SAMImageSearchPlugin(**ImageSearchPlugin.example_manifest())  # type: ignore[arg-type]
        self.assertEqual(manifest.spec.imageSearchData.searchParams.safesearch, "strict")
        self.assertIn("wikimedia.org", manifest.spec.imageSearchData.filters.allowedDomains)  # type: ignore[arg-type]

    # =========================================================================
    # manifest validation
    # =========================================================================
    def test_spec_defaults(self):
        """Test the defaults of the manifest spec."""
        data = ImageSearchData()
        self.assertEqual(data.apiKey, DEFAULT_API_KEY_SECRET_NAME)
        self.assertEqual(DEFAULT_API_KEY_SECRET_NAME, "brave_search_api_key")
        self.assertEqual(data.searchParams.count, 10)
        self.assertEqual(data.searchParams.safesearch, "strict")
        self.assertTrue(data.searchParams.spellcheck)
        self.assertIsNone(data.filters.fileType)
        self.assertTrue(data.validateUrls)

    def test_spec_validation(self):
        """Test that the manifest spec validates and normalizes its search parameters and filters."""
        params = ImageSearchParams(country="US", searchLang="PT-BR", safesearch="OFF")
        self.assertEqual((params.country, params.searchLang, params.safesearch), ("us", "pt-br", "off"))
        self.assertIsNone(ImageSearchParams(country="", searchLang=" ").country)
        self.assertEqual(ImageSearchData(queryTerms="  a   b ").queryTerms, "a b")
        self.assertIsNone(ImageSearchData(queryTerms=" ").queryTerms)
        self.assertIsNone(ImageSearchData().queryTerms)
        self.assertEqual(ImageSearchParams(country="ALL").country, "all")
        filters = ImageSearchFilters(fileType="JPEG | png|jpg", allowedDomains=["WWW.Example.com"])
        self.assertEqual(filters.fileType, "jpg|png")
        self.assertEqual(filters.allowedDomains, ["www.example.com"])
        for model, kwargs in (
            (ImageSearchParams, {"safesearch": "moderate"}),
            (ImageSearchParams, {"country": "usa"}),
            (ImageSearchParams, {"searchLang": "english"}),
            (ImageSearchParams, {"count": 0}),
            (ImageSearchParams, {"count": 21}),
            (ImageSearchFilters, {"fileType": "tiff"}),
            (ImageSearchFilters, {"minWidth": 0}),
            (ImageSearchFilters, {"blockedDomains": ["not a domain"]}),
            (ImageSearchData, {"apiKey": " "}),
        ):
            with self.assertRaises((ValidationError, SAMValidationError), msg=kwargs):
                model(**kwargs)

    def test_normalizers(self):
        """Test the normalizers of the search parameters and filters."""
        self.assertIsNone(normalize_file_types(None))
        self.assertIsNone(normalize_file_types(" | "))
        with self.assertRaises(ValueError):
            normalize_file_types(1)
        self.assertIsNone(normalize_country(None))
        self.assertIsNone(normalize_search_lang(None))

    # =========================================================================
    # helpers
    # =========================================================================
    def test_is_https_url(self):
        """Test that only https urls with a host are accepted."""
        self.assertTrue(is_https_url(CAT))
        for url in ("http://example.com/a.png", "https:///a.png", "ftp://example.com/a.png", None, 42, "https://[::1"):
            self.assertFalse(is_https_url(url), url)

    def test_file_types(self):
        """Test that file types are determined from url extensions, and from Content-Types."""
        self.assertEqual(file_type_of_url("https://x.example/a/B.JPEG?size=large"), "jpg")
        self.assertEqual(file_type_of_url("https://x.example/logo%2Esvg"), "svg")
        self.assertIsNone(file_type_of_url(PHOTO))
        self.assertIsNone(file_type_of_url("https://x.example/a.tiff"))
        self.assertEqual(file_type_of_content_type("image/svg+xml; charset=utf-8"), "svg")
        self.assertEqual(file_type_of_content_type("image/vnd.microsoft.icon"), "ico")
        self.assertIsNone(file_type_of_content_type("text/html"))
        self.assertIsNone(file_type_of_content_type(None))

    def test_as_dimension(self):
        """Test that reported image dimensions are positive ints, or None."""
        self.assertEqual(as_dimension("640"), 640)
        for value in (None, True, "wide", 0, -1):
            self.assertIsNone(as_dimension(value), value)

    def test_parse_brave_images(self):
        """Test that Brave results become ImageResults, and malformed results are skipped."""
        self.assertEqual(parse_brave_images(None), [])
        self.assertEqual(parse_brave_images({"results": "x"}), [])
        images = parse_brave_images(
            {"results": ["x", {"properties": "x"}, {"properties": {"url": " "}}, brave_result(CAT, page_url=" ")]}
        )
        self.assertEqual(images, [ImageResult(url=CAT, page_url=None, width=800, height=None)])

    def test_describe_brave_error(self):
        """Test that Brave errors are described without disclosing the api key."""
        self.assertIn("rejected the api key", describe_brave_error(SafeHttpError("x", status_code=401)))
        self.assertIn("rejected the search parameters", describe_brave_error(SafeHttpError("x", status_code=422)))
        self.assertIn("quota", describe_brave_error(SafeHttpError("x", status_code=429)))
        self.assertIn("HTTP 500", describe_brave_error(SafeHttpError("x", status_code=500)))
        self.assertIn("could not be reached", describe_brave_error(SafeHttpError("x")))

    # =========================================================================
    # tool calls
    # =========================================================================
    def test_custom_tool(self):
        """Test the tool definition presented to the LLM."""
        function = self.load().custom_tool["function"]  # type: ignore[index]
        self.assertEqual(function["parameters"]["required"], ["query"])
        self.assertEqual(function["parameters"]["properties"]["count"]["maximum"], 3)
        self.assertIn("Finds kid-friendly images", function["description"])

    def test_search(self):
        """Test that a search returns only the filtered and validated https image urls, in order."""
        urls, fake = self.call({"query": "kittens"})
        self.assertEqual(urls, [CAT, DOG, PHOTO])
        brave = self.brave_calls(fake)
        self.assertEqual(len(brave), 1)
        self.assertEqual(brave[0]["method"], "GET")
        self.assertEqual(brave[0]["headers"]["X-Subscription-Token"], API_KEY)
        self.assertEqual(
            brave[0]["params"],
            {
                "q": "kittens cartoon",
                "count": 50,
                "country": "US",
                "search_lang": "en",
                "safesearch": "strict",
                "spellcheck": "false",
            },
        )
        heads = [call["url"] for call in fake.calls if call["method"] == "HEAD"]
        self.assertNotIn("http://insecure.example.com/bird.png", heads)
        for url in ("tiny.png", "blocked.png", "animation.gif", "unknown-size.png"):
            self.assertNotIn(f"https://images.example.com/{url}", heads)
        self.assertIn(MISSING, heads)
        self.assertIn(HOTLINK, heads)

    def test_search_json_arguments_and_count(self):
        """Test a tool call whose arguments are a JSON string, with a smaller count."""
        urls, fake = self.call(json.dumps({"query": "kittens", "count": 1}))
        self.assertEqual(urls, [CAT])
        self.assertEqual(self.brave_calls(fake)[0]["params"]["count"], 50)

    def test_search_is_cached(self):
        """Test that search results are cached."""
        first, _ = self.call({"query": "kittens"})
        second, fake = self.call({"query": "kittens"})
        self.assertEqual(first, second)
        self.assertEqual(fake.requested, [])

    def test_search_without_validation(self):
        """Test that, without url validation, no image url is requested, and urls without a file type are dropped."""
        plugin = self.new_plugin("test_image_search_no_validation", validateUrls=False, cacheTtl=0)
        urls, fake = self.call({"query": "kittens"}, plugin=plugin)
        self.assertEqual(urls, [CAT, MISSING, DOG])
        self.assertEqual(fake.requested, [BRAVE_IMAGE_SEARCH_URL])

    def test_search_allowed_domains(self):
        """Test that allowed domains become site: operators, and images from other web pages are dropped."""
        plugin = self.new_plugin(
            "test_image_search_allowed",
            filters={"allowedDomains": ["wikimedia.org", "nasa.gov"]},
            validateUrls=False,
            cacheTtl=0,
        )
        results = [brave_result(CAT, page_url="https://commons.wikimedia.org/wiki/cat"), brave_result(DOG)]
        urls, fake = self.call({"query": "kittens"}, plugin=plugin, host=web(results))
        self.assertEqual(urls, [CAT])
        self.assertEqual(
            self.brave_calls(fake)[0]["params"]["q"], "kittens cartoon (site:wikimedia.org OR site:nasa.gov)"
        )

    def test_search_blocks_images_on_blocked_domains(self):
        """Test that blocked domains also apply to the image url, not only to its web page."""
        plugin = self.new_plugin(
            "test_image_search_blocked_image",
            filters={"blockedDomains": ["blocked.example"]},
            validateUrls=False,
            cacheTtl=0,
        )
        results = [
            brave_result("https://media.blocked.example/cat.png", page_url="https://www.blocked.fr/cat"),
            brave_result(DOG, page_url="https://www.blocked.fr/dog"),
        ]
        urls, _ = self.call({"query": "kittens"}, plugin=plugin, host=web(results))
        self.assertEqual(urls, [DOG])

    def test_search_without_filters(self):
        """Test that, without filters, any https image url is returned, and that more images are requested from Brave."""
        plugin = self.new_plugin(
            "test_image_search_no_filters",
            searchParams={"count": 20},
            filters={},
            validateUrls=False,
            cacheTtl=0,
        )
        urls, fake = self.call({"query": "kittens", "count": True}, plugin=plugin)
        self.assertEqual(self.brave_calls(fake)[0]["params"]["count"], 100)
        self.assertEqual(
            urls,
            [
                CAT,
                "https://images.example.com/tiny.png",
                "https://images.example.com/blocked.png",
                "https://images.example.com/animation.gif",
                MISSING,
                HOTLINK,
                "https://images.example.com/unknown-size.png",
                DOG,
                PHOTO,
            ],
        )

    def test_llm_search_params(self):
        """Test that, if llmSearchParams, the LLM sets every search parameter, and the manifest's are defaults."""
        plugin = self.new_plugin("test_image_search_open", llmSearchParams=True, validateUrls=False, cacheTtl=0)
        tool = plugin.custom_tool["function"]  # type: ignore[index]
        properties = tool["parameters"]["properties"]
        self.assertEqual(set(properties), {"query", "count", "country", "search_lang", "safesearch", "spellcheck"})
        self.assertEqual(properties["count"]["maximum"], 20)
        self.assertEqual(properties["safesearch"]["enum"], ["off", "strict"])
        self.assertIn("search_lang", tool["description"])
        args = {
            "query": "tour de france",
            "count": 15,
            "country": "FR",
            "search_lang": "fr",
            "safesearch": "off",
            "spellcheck": True,
        }
        _, fake = self.call(args, plugin=plugin)
        self.assertEqual(
            self.brave_calls(fake)[0]["params"],
            {
                "q": "tour de france cartoon",
                "count": 75,
                "country": "FR",
                "search_lang": "fr",
                "safesearch": "off",
                "spellcheck": "true",
            },
        )

    def test_llm_search_params_invalid_values_use_defaults(self):
        """Test that invalid search parameters from the LLM are ignored, in favor of the manifest's."""
        plugin = self.new_plugin("test_image_search_open_invalid", llmSearchParams=True, validateUrls=False, cacheTtl=0)
        args = {
            "query": "kittens",
            "country": "France",
            "search_lang": "",
            "safesearch": "moderate",
            "spellcheck": "yes",
        }
        _, fake = self.call(args, plugin=plugin)
        params = self.brave_calls(fake)[0]["params"]
        self.assertEqual(
            (params["country"], params["search_lang"], params["safesearch"], params["spellcheck"]),
            ("US", "en", "strict", "false"),
        )

    def test_llm_search_params_off(self):
        """Test that, unless llmSearchParams, the LLM's search parameters are ignored, and count is capped."""
        args = {"query": "kittens", "count": 15, "country": "fr", "safesearch": "off"}
        _, fake = self.call(args)
        params = self.brave_calls(fake)[0]["params"]
        self.assertEqual((params["country"], params["safesearch"], params["count"]), ("US", "strict", 50))
        self.assertNotIn("country", self.load().custom_tool["function"]["parameters"]["properties"])  # type: ignore[index]

    def test_invalid_arguments(self):
        """Test that invalid arguments return an empty list, without searching."""
        for args in (None, "", "not json", "[1]", {"query": ""}, {"query": 42}, {"count": 2}):
            urls, fake = self.call(args)
            self.assertEqual(urls, [], args)
            self.assertEqual(fake.requested, [], args)

    def test_brave_failure(self):
        """Test that a failed search returns an empty list, and logs why, without the api key."""
        with self.assertLogs(LOGGER, level="WARNING") as logs:
            urls, _ = self.call({"query": "kittens"}, host=web([], status_code=401))
        self.assertEqual(urls, [])
        output = "\n".join(logs.output)
        self.assertIn("rejected the api key", output)
        self.assertNotIn(API_KEY, output)

    def test_brave_invalid_response(self):
        """Test that an invalid Brave response returns an empty list."""
        host = web()
        host.add(BRAVE_IMAGE_SEARCH_URL, b"not json", 200, {"Content-Type": "application/json"})
        with self.assertLogs(LOGGER, level="WARNING") as logs:
            urls, _ = self.call({"query": "kittens"}, host=host)
        self.assertEqual(urls, [])
        self.assertIn("invalid response", "\n".join(logs.output))

    def test_missing_api_key(self):
        """Test that a missing api key returns an empty list, and logs how to create it."""
        plugin = self.new_plugin("test_image_search_no_api_key", apiKey="no_such_secret")
        with self.assertLogs(LOGGER, level="WARNING") as logs:
            urls, fake = self.call({"query": "kittens"}, plugin=plugin)
        self.assertEqual(urls, [])
        self.assertEqual(fake.requested, [])
        output = "\n".join(logs.output)
        self.assertIn("no_such_secret", output)
        self.assertIn("api-dashboard.search.brave.com", output)
        self.assertIn("SMARTER_BRAVE_SEARCH_API_KEY", output)

    def test_unreadable_api_key(self):
        """Test that an api key Secret that cannot be decrypted returns an empty list."""
        with (
            mock.patch("smarter.apps.secret.models.Secret.get_secret", side_effect=SmarterValueError("bad")),
            self.assertLogs(LOGGER, level="WARNING"),
        ):
            urls, _ = self.call({"query": "kittens"})
        self.assertEqual(urls, [])

    def test_not_ready(self):
        """Test that a plugin that is not ready raises."""
        plugin = self.load()
        with mock.patch.object(ImageSearchPlugin, "ready", new_callable=mock.PropertyMock, return_value=False):
            with self.assertRaises(SmarterImageSearchPluginError):
                plugin.tool_call_fetch_plugin_response({"query": "kittens"})
            self.assertIsNone(plugin.custom_tool)
            self.assertIsNone(plugin.to_json())

    # =========================================================================
    # samples
    # =========================================================================
    def test_sample_manifests(self):
        """Test that every sample ImageSearchPlugin manifest is valid, and can be applied."""
        paths = sorted(glob.glob(os.path.join(SAMPLE_PLUGINS_PATH, "image-search*.yaml")))
        self.assertEqual(len(paths), 5)
        for path in paths:
            data = copy.deepcopy(get_readonly_yaml_file(path))
            data["metadata"]["name"] = f"{data['metadata']['name']}_{self.hash_suffix}"  # type: ignore[index]
            manifest = SAMImageSearchPlugin(**data)  # type: ignore[arg-type]
            self.assertEqual(manifest.kind, MANIFEST_KIND)
            self.assertEqual(manifest.spec.imageSearchData.apiKey, DEFAULT_API_KEY_SECRET_NAME)
            plugin = ImageSearchPlugin(manifest=manifest, user_profile=self.user_profile)
            self.addCleanup(self.delete_plugin_by_id, plugin.id)
            self.assertTrue(plugin.ready, path)

    def test_weather_llmclient_finds_the_image_search_tool(self):
        """
        Test that the weather LLMClient's system prompt can identify the image_search tool.

        The LLM sees the plugin under a generated function name, not ``image_search``, so the
        prompt identifies the tool by the opening words of its description.
        """
        weather = get_readonly_yaml_file(os.path.join(LLMCLIENTS_PATH, "llmclient-weather.yaml"))
        self.assertIn("get_current_weather", weather["spec"]["functions"])
        self.assertIn("image_search", weather["spec"]["plugins"])
        system_role = weather["spec"]["config"]["defaultSystemRole"]
        self.assertIn(f'description begins "{WEATHER_IMAGE_SEARCH_DESCRIPTION}"', system_role)

        data = copy.deepcopy(get_readonly_yaml_file(os.path.join(SAMPLE_PLUGINS_PATH, "image-search.yaml")))
        self.assertEqual(data["metadata"]["name"], "image_search")
        data["metadata"]["name"] = f"{data['metadata']['name']}_{self.hash_suffix}"  # type: ignore[index]
        plugin = ImageSearchPlugin(manifest=SAMImageSearchPlugin(**data), user_profile=self.user_profile)  # type: ignore[arg-type]
        self.addCleanup(self.delete_plugin_by_id, plugin.id)
        function = plugin.custom_tool["function"]  # type: ignore[index]
        self.assertNotEqual(function["name"], "image_search")
        self.assertTrue(function["description"].startswith(WEATHER_IMAGE_SEARCH_DESCRIPTION))
