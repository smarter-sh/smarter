"""
Smarter API Manifest - LLMClient.spec.config.styles.

The look of the chat in which an LLMClient's users talk to it: Smarter Chat, the
``@smarter.sh/ui-chat`` React component, which the Smarter workbench and every page that embeds the
LLMClient render. Smarter Chat is built on chatscope's ``@chatscope/chat-ui-kit-react`` components and
their ``@chatscope/chat-ui-kit-styles`` theme, so these settings follow that theme's design: one
section per chatscope component (the main container, the conversation header, the message list,
incoming and outgoing messages, the message input, the buttons and the typing indicator), and in each
section, the theme's own variables for it, such as ``$conversation-header-bg-color``.

Every setting is optional. A setting that is left out keeps chatscope's (or Smarter's) default, so
a manifest needs only what it changes. Values are validated here, because they are written into the
pages of every site that embeds the LLMClient: colors, lengths and font names must be plain css
values, and images must be ``https`` urls. When a client sends a manifest, to apply or validate it,
each image url is also requested, and must respond with an image: HTTP 200, directly or after
redirects. See :func:`validate_image_url_is_available`.
"""

import os
import re
from typing import ClassVar, Literal, Optional

from pydantic import ConfigDict, Field, field_validator

from smarter.apps.llmclient.manifest.models.llmclient.const import MANIFEST_KIND
from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, fetch
from smarter.lib.manifest.models import AbstractSAMSpecBase, is_client_manifest

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

CSS_COLOR_PATTERN = re.compile(
    r"^(#[0-9a-fA-F]{3,4}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{8}"
    r"|(rgb|rgba|hsl|hsla)\(\s*[0-9.%\s,/+-]+\)"
    r"|[a-zA-Z]{3,30})$"
)
"""
A css color: a hex color (``#ff5733``, ``#f53``, ``#ff573380``), an ``rgb()``, ``rgba()``,.

``hsl()`` or ``hsla()`` color of plain numbers, or a color name (``tomato``, ``transparent``).
"""

CSS_LENGTH_PATTERN = re.compile(r"^(0|\d{1,4}(\.\d{1,3})?(px|em|rem|%))$")
"""A css length: a number and a unit, ``px``, ``em``, ``rem`` or ``%`` (``16px``, ``1.1em``), or ``0``."""

CSS_FONT_FAMILY_PATTERN = re.compile(r"^[A-Za-z0-9 ,'\"_-]{1,200}$")
"""A css font stack: font names separated by commas (``"Fredoka", system-ui, sans-serif``)."""

GOOGLE_FONT_PATTERN = re.compile(r"^[A-Za-z0-9 ]{1,64}$")
"""The name of a font in the Google Fonts catalog (``Fredoka``, ``Space Grotesk``)."""

IMAGE_URL_PATTERN = re.compile(r"^https://[^\s\"'()<>\\]{1,2048}$")
"""An ``https`` url, without the characters that could end a css ``url()``."""

IMAGE_URL_TIMEOUT = 10
"""Seconds to wait for an image url to respond."""

NOT_AN_IMAGE_CONTENT_TYPES = ("text/", "application/json", "application/xml")
"""The Content-Types of responses that are not images, e.g. a web page that shows the image."""


def _validate(value: Optional[str], pattern: re.Pattern, field: str, example: str) -> Optional[str]:
    """
    Check a style value against its pattern.

    :param value: The value, or ``None``.
    :type value: Optional[str]
    :param pattern: The pattern that a valid value matches.
    :type pattern: re.Pattern
    :param field: The name of the setting, for the error message.
    :type field: str
    :param example: Examples of valid values, for the error message.
    :type example: str
    :returns: The value, stripped of surrounding white space, or ``None``.
    :rtype: Optional[str]
    :raises ValueError: If the value doesn't match the pattern.
    """
    if value is None:
        return None
    value = str(value).strip()
    if not pattern.match(value):
        raise ValueError(f"{field}: {value!r} is not valid. Use a value such as {example}.")
    return value


def validate_color(value: Optional[str]) -> Optional[str]:
    """
    Validate a css color.

    :param value: The color, or ``None``.
    :type value: Optional[str]
    :returns: The color, or ``None``.
    :rtype: Optional[str]
    :raises ValueError: If the value is not a color.
    """
    return _validate(value, CSS_COLOR_PATTERN, "color", "'#ff5733', 'rgba(0, 0, 0, 0.5)' or 'tomato'")


def validate_length(value: Optional[str]) -> Optional[str]:
    """
    Validate a css length.

    :param value: The length, or ``None``.
    :type value: Optional[str]
    :returns: The length, or ``None``.
    :rtype: Optional[str]
    :raises ValueError: If the value is not a length.
    """
    return _validate(value, CSS_LENGTH_PATTERN, "length", "'16px', '1.1em', '1rem' or '0'")


def validate_font_family(value: Optional[str]) -> Optional[str]:
    """
    Validate a css font stack.

    :param value: The font stack, or ``None``.
    :type value: Optional[str]
    :returns: The font stack, or ``None``.
    :rtype: Optional[str]
    :raises ValueError: If the value is not a font stack.
    """
    return _validate(value, CSS_FONT_FAMILY_PATTERN, "fontFamily", "'\"Fredoka\", system-ui, sans-serif'")


def validate_image_url(value: Optional[str]) -> Optional[str]:
    """
    Validate the url of an image.

    :param value: The url, or ``None``.
    :type value: Optional[str]
    :returns: The url, or ``None``.
    :rtype: Optional[str]
    :raises ValueError: If the value is not an ``https`` url.
    """
    return _validate(value, IMAGE_URL_PATTERN, "url", "'https://cdn.example.com/images/logo.png'")


def validate_image_url_is_available(url: str) -> None:
    """
    Validate that an image url responds with an image.

    The url is requested with HEAD, or with GET if the server doesn't allow HEAD, through
    :func:`smarter.apps.llmtool.plugin.safe_http.fetch`, which refuses urls that aren't public
    (server-side request forgery), and follows redirects, validating each one. The response must
    be HTTP 200, directly or after redirects (e.g. a 301), and must not be a web page. The result is
    not cached, so that each apply checks that the url is still available.

    :param url: The ``https`` url of an image.
    :type url: str
    :raises ValueError: If the url doesn't respond with an image.
    """
    try:
        try:
            response = fetch(url, method="HEAD", timeout=IMAGE_URL_TIMEOUT)
        except SafeHttpError as e:
            if e.status_code not in (403, 405, 501):
                raise
            # some servers and CDNs answer only GET. The image is read, but not kept.
            response = fetch(url, timeout=IMAGE_URL_TIMEOUT, max_bytes=20_000_000)
    except SafeHttpError as e:
        raise ValueError(f"{url} is not available: {e}. Open it in a browser to check it.") from e
    if response.content_type.startswith(NOT_AN_IMAGE_CONTENT_TYPES):
        raise ValueError(
            f"{url} is a {response.content_type} page, not an image. Use the url of the image itself, which "
            "usually ends with .png, .jpg, .svg or .webp."
        )


class SAMLLMClientStyleSection(AbstractSAMSpecBase):
    """
    Base class of the sections of ``spec.config.styles``.

    A section's colors are validated as css colors, and a misspelled setting is an error, rather
    than being ignored.
    """

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def validate_colors(cls, value, info):
        """
        Validate every color setting, ``color`` and those whose names end with ``Color``, as a css color.

        :param value: The setting's value.
        :param info: Pydantic's validation info, with the setting's name.
        :returns: The value.
        :raises ValueError: If a color setting is not a css color.
        """
        if info.field_name == "color" or info.field_name.endswith("Color"):
            return validate_color(value)
        return value


class SAMLLMClientStylesMainContainer(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.mainContainer``: the frame around the whole chat.

    chatscope's ``MainContainer``, class ``.cs-main-container``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".mainContainer"

    backgroundColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.backgroundColor[str]. Optional. The color behind the whole chat. chatscope's $main-container-bg-color. Example: '#ffffff'.",
    )
    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The default text color of the chat. chatscope's $main-container-color. Example: '#212121'.",
    )
    borderColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.borderColor[str]. Optional. The color of the line around the chat. chatscope's $main-container-border. Example: '#ff5733'.",
    )


class SAMLLMClientStylesConversationHeader(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.conversationHeader``: the bar at the top of the chat.

    It holds the logo, the LLMClient's name, its model, and the buttons. chatscope's
    ``ConversationHeader``, class ``.cs-conversation-header``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".conversationHeader"

    backgroundColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.backgroundColor[str]. Optional. The header's background color. chatscope's $conversation-header-bg-color. Example: '#1b1f3b'.",
    )
    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The color of the LLMClient's name, and of the header's buttons: new chat, show or hide the Console, sandbox or production, and Docs. Choose a color that contrasts with backgroundColor. chatscope's $conversation-header-user-name-color. Example: '#ffffff'.",
    )
    infoColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.infoColor[str]. Optional. The color of the line under the name, which names the LLM provider and model. chatscope's $conversation-header-info-color. Example: '#c0c4e0'.",
    )
    borderColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.borderColor[str]. Optional. The color of the line under the header. chatscope's $conversation-header-border-bottom. Example: '#ff5733'.",
    )


class SAMLLMClientStylesMessageList(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.messageList``: the scrolling area that holds the conversation.

    It is painted over ``appBackgroundImageUrl``, so a semi-transparent ``backgroundColor`` tints the
    image. chatscope's ``MessageList``, class ``.cs-message-list``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".messageList"

    backgroundColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.backgroundColor[str]. Optional. The color of the conversation's background. Over a background image, use a semi-transparent color, such as 'rgba(255, 255, 255, 0.6)', which tints the image. chatscope's $message-list-bg-color. Example: '#f6fbff'.",
    )
    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The color of text in the conversation outside of the messages, such as the typing indicator's. chatscope's $message-list-color. Example: '#212121'.",
    )


class SAMLLMClientStylesMessage(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.incomingMessage`` and ``outgoingMessage``: the message bubbles.

    Incoming messages are the assistant's, on the left. Outgoing messages are the user's, on the
    right. chatscope's ``Message``, classes ``.cs-message--incoming`` and ``.cs-message--outgoing``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".message"

    backgroundColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.backgroundColor[str]. Optional. The bubble's color. chatscope's $message-content-incoming-bg-color and $message-content-outgoing-bg-color. Example: '#c6e3fa'.",
    )
    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The color of the text in the bubble. chatscope's $message-content-incoming-color and $message-content-outgoing-color. Example: '#212121'.",
    )
    borderColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.borderColor[str]. Optional. The color of a thin line around the bubble, which has none by default. Example: '#6ea9d7'.",
    )
    linkColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.linkColor[str]. Optional. The color of links in the bubble. Example: '#0b57d0'.",
    )


class SAMLLMClientStylesMessageInput(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.messageInput``: the box at the bottom, in which the user types.

    chatscope's ``MessageInput``, class ``.cs-message-input``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".messageInput"

    backgroundColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.backgroundColor[str]. Optional. The color of the strip around the box. chatscope's $message-input-bg-color. Example: '#ffffff'.",
    )
    editorBackgroundColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.editorBackgroundColor[str]. Optional. The color of the box itself. chatscope's $message-input-content-editor-wrapper-bg-color. Example: '#c6e3fa'.",
    )
    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The color of the text that the user types. chatscope's $message-input-content-editor-color. Example: '#212121'.",
    )
    placeholderColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.placeholderColor[str]. Optional. The color of the placeholder, the hint in the empty box (spec.config.prompt.appPlaceholder). chatscope's $message-input-placeholder-color. Example: '#9e9e9e'.",
    )
    borderColor: Optional[str] = Field(
        None,
        description=f"{class_identifier}.borderColor[str]. Optional. The color of the line above the box. chatscope's $chat-container-message-input-border-top. Example: '#d1dbe3'.",
    )


class SAMLLMClientStylesButtons(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.buttons``: the send and attach buttons, on the message input.

    The header's buttons take the header's text color, ``conversationHeader.color``, so that
    they contrast with the header, whose background is usually the opposite of the input's.

    chatscope's ``Button``, class ``.cs-button``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".buttons"

    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The color of the send and attach buttons' icons, on the message input. The header's buttons use conversationHeader.color, or this color if it is not set. chatscope's $button-color. Example: '#6ea9d7'.",
    )


class SAMLLMClientStylesTypingIndicator(SAMLLMClientStyleSection):
    """
    ``spec.config.styles.typingIndicator``: "Assistant is typing", and its dots, while the LLM answers.

    chatscope's ``TypingIndicator``, class ``.cs-typing-indicator``.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".typingIndicator"

    color: Optional[str] = Field(
        None,
        description=f"{class_identifier}.color[str]. Optional. The color of the text and of the animated dots. chatscope's $typing-indicator-text-color and $typing-indicator-dot-bg-color. Example: '#6ea9d7'.",
    )


class SAMLLMClientSpecConfigStyles(SAMLLMClientStyleSection):
    """
    Smarter API LLMClient Manifest LLMClient.spec.config.styles.

    The look of Smarter Chat for this LLMClient. Every setting is optional. See the module's docstring.
    """

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    appLogoUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.appLogoUrl[str]. Optional. The url of the LLMClient's logo, a square image that is displayed in a circle at the left of the chat's header, and on the LLMClient's card in the web console. chatscope's Avatar. Example: 'https://cdn.example.com/images/logo.png'.",
    )
    appBackgroundImageUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.appBackgroundImageUrl[str]. Optional. The url of an image that is displayed behind the conversation. Choose a quiet image, so that the messages stay readable, or tint it with a semi-transparent messageList.backgroundColor. Example: 'https://cdn.example.com/images/background.png'.",
    )
    appBackgroundImageSize: Optional[Literal["cover", "contain", "auto"]] = Field(
        None,
        description=f"{class_identifier}.appBackgroundImageSize[str]. Optional. How the background image fills the conversation: 'cover' (the default) fills it and crops the image's edges, 'contain' shows the whole image, and 'auto' shows the image at its own size, repeated like tiles.",
    )
    assistantAvatarUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.assistantAvatarUrl[str]. Optional. The url of a small square picture, displayed in a circle beside each of the assistant's messages. chatscope's Message Avatar. Example: 'https://cdn.example.com/images/assistant.png'.",
    )
    userAvatarUrl: Optional[str] = Field(
        None,
        description=f"{class_identifier}.userAvatarUrl[str]. Optional. The url of a small square picture, displayed in a circle beside each of the user's messages. chatscope's Message Avatar. Example: 'https://cdn.example.com/images/user.png'.",
    )
    fontFamily: Optional[str] = Field(
        None,
        description=f"{class_identifier}.fontFamily[str]. Optional. The chat's fonts, the first that the visitor's browser has, in order. chatscope's $default-font-family. Example: '\"Fredoka\", system-ui, sans-serif'.",
    )
    googleFont: Optional[str] = Field(
        None,
        description=f"{class_identifier}.googleFont[str]. Optional. The name of a font from https://fonts.google.com, which the chat downloads. When fontFamily is not set, the chat uses this font. Example: 'Fredoka'.",
    )
    fontSize: Optional[str] = Field(
        None,
        description=f"{class_identifier}.fontSize[str]. Optional. The size of the chat's text, of which every other size is a proportion. chatscope's $main-container-font-size. Example: '16px' or '1.1rem'.",
    )
    borderRadius: Optional[str] = Field(
        None,
        description=f"{class_identifier}.borderRadius[str]. Optional. How round the corners of the message bubbles and of the message input box are. '0' is square. chatscope's $default-border-radius. Example: '0.7em' (the default) or '18px'.",
    )
    mainContainer: Optional[SAMLLMClientStylesMainContainer] = Field(
        None, description=f"{class_identifier}.mainContainer[object]. Optional. The frame around the whole chat."
    )
    conversationHeader: Optional[SAMLLMClientStylesConversationHeader] = Field(
        None, description=f"{class_identifier}.conversationHeader[object]. Optional. The bar at the top of the chat."
    )
    messageList: Optional[SAMLLMClientStylesMessageList] = Field(
        None, description=f"{class_identifier}.messageList[object]. Optional. The area that holds the conversation."
    )
    incomingMessage: Optional[SAMLLMClientStylesMessage] = Field(
        None,
        description=f"{class_identifier}.incomingMessage[object]. Optional. The assistant's message bubbles, on the left.",
    )
    outgoingMessage: Optional[SAMLLMClientStylesMessage] = Field(
        None,
        description=f"{class_identifier}.outgoingMessage[object]. Optional. The user's message bubbles, on the right.",
    )
    messageInput: Optional[SAMLLMClientStylesMessageInput] = Field(
        None, description=f"{class_identifier}.messageInput[object]. Optional. The box in which the user types."
    )
    buttons: Optional[SAMLLMClientStylesButtons] = Field(
        None, description=f"{class_identifier}.buttons[object]. Optional. The chat's buttons."
    )
    typingIndicator: Optional[SAMLLMClientStylesTypingIndicator] = Field(
        None,
        description=f"{class_identifier}.typingIndicator[object]. Optional. The indicator that the assistant is answering.",
    )

    @field_validator("appLogoUrl", "appBackgroundImageUrl", "assistantAvatarUrl", "userAvatarUrl")
    @classmethod
    def validate_urls(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate the images' urls, and, in a manifest that a client sent, that each is available.

        See :func:`smarter.lib.manifest.models.client_manifest_validation`.

        :param value: The url, or ``None``.
        :type value: Optional[str]
        :returns: The url, or ``None``.
        :rtype: Optional[str]
        :raises ValueError: If the url is not an ``https`` url, or, in a client's manifest, doesn't
            respond with an image.
        """
        url = validate_image_url(value)
        if url and is_client_manifest():
            validate_image_url_is_available(url)
        return url

    @field_validator("fontFamily")
    @classmethod
    def validate_font_family(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate ``fontFamily``.

        :param value: The font stack, or ``None``.
        :type value: Optional[str]
        :returns: The font stack, or ``None``.
        :rtype: Optional[str]
        :raises ValueError: If the value is not a font stack.
        """
        return validate_font_family(value)

    @field_validator("googleFont")
    @classmethod
    def validate_google_font(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate ``googleFont``.

        :param value: The font's name, or ``None``.
        :type value: Optional[str]
        :returns: The font's name, or ``None``.
        :rtype: Optional[str]
        :raises ValueError: If the value is not the name of a font.
        """
        return _validate(value, GOOGLE_FONT_PATTERN, "googleFont", "'Fredoka' or 'Space Grotesk'")

    @field_validator("fontSize", "borderRadius")
    @classmethod
    def validate_lengths(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate ``fontSize`` and ``borderRadius``.

        :param value: The length, or ``None``.
        :type value: Optional[str]
        :returns: The length, or ``None``.
        :rtype: Optional[str]
        :raises ValueError: If the value is not a length.
        """
        return validate_length(value)


__all__ = [
    "SAMLLMClientSpecConfigStyles",
    "SAMLLMClientStyleSection",
    "SAMLLMClientStylesButtons",
    "SAMLLMClientStylesConversationHeader",
    "SAMLLMClientStylesMainContainer",
    "SAMLLMClientStylesMessage",
    "SAMLLMClientStylesMessageInput",
    "SAMLLMClientStylesMessageList",
    "SAMLLMClientStylesTypingIndicator",
    "validate_color",
    "validate_font_family",
    "validate_image_url",
    "validate_image_url_is_available",
    "validate_length",
]
