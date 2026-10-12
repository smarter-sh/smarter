"""Test the LLMClient manifest's spec.config.styles."""

from unittest.mock import patch

from pydantic import ValidationError

from smarter.apps.llmclient.manifest.models.llmclient.styles import (
    SAMLLMClientSpecConfigStyles,
    SAMLLMClientStylesConversationHeader,
    SAMLLMClientStylesMessage,
    validate_color,
    validate_font_family,
    validate_image_url,
    validate_image_url_is_available,
    validate_length,
)
from smarter.apps.plugin.plugin.safe_http import SafeHttpError, SafeResponse
from smarter.lib.manifest.models import client_manifest_validation
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestLLMClientStylesValidators(SmarterTestBase):
    """Test the validators of css values."""

    def test_colors(self):
        for color in (
            "#fff",
            "#ffff",
            "#ff5733",
            "#ff573380",
            "rgb(255, 87, 51)",
            "rgba(0, 0, 0, 0.5)",
            "rgb(255 87 51 / 50%)",
            "hsl(10, 100%, 60%)",
            "hsla(10, 100%, 60%, .5)",
            "tomato",
            "transparent",
        ):
            with self.subTest(color=color):
                self.assertEqual(validate_color(f" {color} "), color)

    def test_invalid_colors(self):
        for color in (
            "#ff57a",
            "#gg5733",
            "url(https://evil.example.com/x.png)",
            "red; background: blue",
            "rgb(0,0,0)}",
            "expression(alert(1))",
            "var(--x)",
            "",
        ):
            with self.subTest(color=color):
                with self.assertRaises(ValueError):
                    validate_color(color)

    def test_none(self):
        self.assertIsNone(validate_color(None))
        self.assertIsNone(validate_length(None))
        self.assertIsNone(validate_font_family(None))
        self.assertIsNone(validate_image_url(None))

    def test_lengths(self):
        for length in ("0", "16px", "1.1em", "1rem", "50%", "0.75em"):
            with self.subTest(length=length):
                self.assertEqual(validate_length(length), length)
        for length in ("16", "big", "16pt", "-1px", "calc(1px + 1em)", "1px;"):
            with self.subTest(length=length):
                with self.assertRaises(ValueError):
                    validate_length(length)

    def test_font_families(self):
        self.assertEqual(validate_font_family('"Fredoka", system-ui, sans-serif'), '"Fredoka", system-ui, sans-serif')
        for font in ("Comic Sans; color: red", "a{b}", "url(x)", ""):
            with self.subTest(font=font):
                with self.assertRaises(ValueError):
                    validate_font_family(font)

    def test_image_urls(self):
        self.assertEqual(validate_image_url("https://cdn.smarter.sh/a/b.png?x=1"), "https://cdn.smarter.sh/a/b.png?x=1")
        for url in (
            "javascript:alert(1)",
            "data:image/png;base64,AAAA",
            "ftp://example.com/a.png",
            "http://example.com/a.png",
            'https://example.com/a.png") ; x',
            "https://example.com/a b.png",
            "//example.com/a.png",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_image_url(url)


class TestLLMClientSpecConfigStyles(SmarterTestBase):
    """Test the styles model."""

    def test_everything_is_optional(self):
        styles = SAMLLMClientSpecConfigStyles()
        self.assertEqual(styles.model_dump(exclude_none=True), {})

    def test_complete(self):
        styles = SAMLLMClientSpecConfigStyles(
            appLogoUrl="https://cdn.example.com/logo.png",
            appBackgroundImageUrl="https://cdn.example.com/bg.png",
            appBackgroundImageSize="contain",
            assistantAvatarUrl="https://cdn.example.com/assistant.png",
            userAvatarUrl="https://cdn.example.com/user.png",
            fontFamily='"Fredoka", sans-serif',
            googleFont="Space Grotesk",
            fontSize="15px",
            borderRadius="18px",
            mainContainer={"backgroundColor": "#fff", "color": "#212121", "borderColor": "tomato"},
            conversationHeader={
                "backgroundColor": "#1b1f3b",
                "color": "#fff",
                "infoColor": "#ccc",
                "borderColor": "red",
            },
            messageList={"backgroundColor": "rgba(255, 255, 255, 0.6)", "color": "#000"},
            incomingMessage={"backgroundColor": "#eee", "color": "#111", "borderColor": "#ccc", "linkColor": "blue"},
            outgoingMessage={"backgroundColor": "tomato", "color": "#fff"},
            messageInput={
                "backgroundColor": "#fff",
                "editorBackgroundColor": "#eee",
                "color": "#000",
                "placeholderColor": "#999",
                "borderColor": "#ddd",
            },
            buttons={"color": "tomato"},
            typingIndicator={"color": "tomato"},
        )
        self.assertIsInstance(styles.conversationHeader, SAMLLMClientStylesConversationHeader)
        self.assertIsInstance(styles.incomingMessage, SAMLLMClientStylesMessage)
        self.assertEqual(styles.messageInput.editorBackgroundColor, "#eee")
        self.assertEqual(styles.googleFont, "Space Grotesk")

    def test_misspelled_setting_is_an_error(self):
        with self.assertRaises(ValidationError):
            SAMLLMClientSpecConfigStyles(appLogoURL="https://cdn.example.com/logo.png")
        with self.assertRaises(ValidationError):
            SAMLLMClientSpecConfigStyles(conversationHeader={"bgColor": "#fff"})

    def test_invalid_values(self):
        for kwargs in (
            {"appLogoUrl": "javascript:alert(1)"},
            {"appBackgroundImageSize": "stretch"},
            {"fontSize": "huge"},
            {"borderRadius": "round"},
            {"googleFont": "Fredoka&display=swap"},
            {"fontFamily": "a;b"},
            {"messageList": {"backgroundColor": "url(https://evil.example.com)"}},
            {"buttons": {"color": "red !important"}},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValidationError):
                    SAMLLMClientSpecConfigStyles(**kwargs)


def response(content_type: str = "image/png") -> SafeResponse:
    """A response to a request for an image url."""
    return SafeResponse(
        url="https://cdn.example.com/logo.png", status_code=200, headers={"content-type": content_type}, content=b""
    )


FETCH = "smarter.apps.llmclient.manifest.models.llmclient.styles.fetch"
URL = "https://cdn.example.com/logo.png"


class TestLLMClientStylesImageUrlIsAvailable(SmarterTestBase):
    """Test that a client's manifest's image urls are checked to respond with an image."""

    def test_image(self):
        with patch(FETCH, return_value=response()) as fetch:
            validate_image_url_is_available(URL)
        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.kwargs["method"], "HEAD")

    def test_unavailable(self):
        with patch(FETCH, side_effect=SafeHttpError("cdn.example.com responded with HTTP 404", status_code=404)):
            with self.assertRaisesRegex(ValueError, "is not available"):
                validate_image_url_is_available(URL)

    def test_not_public(self):
        with patch(FETCH, side_effect=SafeHttpError("host must have a public address: localhost")):
            with self.assertRaisesRegex(ValueError, "public address"):
                validate_image_url_is_available(URL)

    def test_web_page(self):
        with patch(FETCH, return_value=response("text/html")):
            with self.assertRaisesRegex(ValueError, "not an image"):
                validate_image_url_is_available(URL)

    def test_get_when_head_is_not_allowed(self):
        with patch(FETCH, side_effect=[SafeHttpError("HTTP 405", status_code=405), response()]) as fetch:
            validate_image_url_is_available(URL)
        self.assertEqual(fetch.call_count, 2)
        self.assertNotIn("method", fetch.call_args.kwargs)

    def test_get_fails_too(self):
        with patch(
            FETCH, side_effect=[SafeHttpError("HTTP 403", status_code=403), SafeHttpError("HTTP 403", status_code=403)]
        ):
            with self.assertRaisesRegex(ValueError, "is not available"):
                validate_image_url_is_available(URL)

    def test_only_a_clients_manifest_is_checked(self):
        """A model built outside of client_manifest_validation(), e.g. from the database, never makes a request."""
        with patch(FETCH, return_value=response()) as fetch:
            SAMLLMClientSpecConfigStyles(appLogoUrl=URL)
            fetch.assert_not_called()
            with client_manifest_validation():
                SAMLLMClientSpecConfigStyles(appLogoUrl=URL, assistantAvatarUrl=URL)
            self.assertEqual(fetch.call_count, 2)
            # the context ends with the block.
            SAMLLMClientSpecConfigStyles(appLogoUrl=URL)
            self.assertEqual(fetch.call_count, 2)

    def test_clients_manifest_with_an_unavailable_image(self):
        with patch(FETCH, side_effect=SafeHttpError("HTTP 404", status_code=404)):
            with self.assertRaises(ValidationError), client_manifest_validation():
                SAMLLMClientSpecConfigStyles(appLogoUrl=URL)
