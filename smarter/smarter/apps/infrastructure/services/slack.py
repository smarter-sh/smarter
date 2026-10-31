"""
The Slack service: the platform's messages to Slack.

Slack does not depend on a cloud: Smarter posts with the `Slack Web API <https://docs.slack.dev/apis/web-api/>`__,
as a Slack app's bot, whose token is ``smarter_settings.slack_bot_token``
(``SMARTER_SLACK_BOT_TOKEN``). So :class:`SlackService` is implemented by
:class:`SlackWebApiService`, for every cloud provider. The bot needs the scopes ``chat:write``, to
post messages, and ``files:write``, to upload files, and must be a member of the channel.

The platform uses it through :data:`smarter.apps.infrastructure.services.infrastructure`
``.slack``. Tests replace it with :func:`configure_slack`, e.g. with :class:`InMemorySlackService`.

.. code-block:: python

    from smarter.apps.infrastructure.services import infrastructure

    message = infrastructure.slack.post_message("smarter", "*Deployed* :white_check_mark:")
    if message:
        infrastructure.slack.upload_file(
            message.channel_id, "job.txt", log.encode("utf-8"), thread_ts=message.ts
        )

A message names its channel by name or id, and :meth:`SlackService.post_message` returns the
channel's id and the message's timestamp, ``ts``, which a file upload, or a reply in the message's
thread, needs. Like email, Slack never breaks the work that posts to it: failures are logged and
returned as None or False, never raised.
"""

import json
from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional, Union
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ConfigDict

from smarter.apps.infrastructure.const import InfrastructureServiceNames
from smarter.apps.infrastructure.exceptions import SlackServiceError
from smarter.apps.infrastructure.services.base import InfrastructureService
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest import running_unit_tests

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

SLACK_API_URL = "https://slack.com/api/"
"""The Slack Web API.

The bot token is sent here, and nowhere else.
"""

SLACK_UPLOAD_DOMAIN = "slack.com"
"""The domain of the upload urls that ``files.getUploadURLExternal`` returns, e.g. ``files.slack.com``."""

REQUEST_TIMEOUT = 30
"""Seconds to wait for a Slack Web API method to respond."""

UPLOAD_TIMEOUT = 120
"""Seconds to wait for a file's upload."""

SlackPayloadType = dict[str, Union[str, int, bool, list[dict[str, str]]]]
"""The arguments of a Slack Web API method."""


class SlackApiResponse(BaseModel):
    """
    The fields of a Slack Web API response that the service reads.

    Each method returns more, which are allowed, and ignored.
    """

    model_config = ConfigDict(extra="allow")

    ok: bool = False
    """Whether the method succeeded."""

    error: Optional[str] = None
    """Why it failed, e.g. ``channel_not_found``, ``not_in_channel`` or ``missing_scope``."""

    needed: Optional[str] = None
    """The scope that a ``missing_scope`` error needs, e.g. ``files:write``."""

    channel: Optional[str] = None
    """``chat.postMessage``: the id of the channel that the message was posted to."""

    ts: Optional[str] = None
    """``chat.postMessage``: the message's timestamp, which is its id in the channel."""

    upload_url: Optional[str] = None
    """``files.getUploadURLExternal``: where to send the file's contents."""

    file_id: Optional[str] = None
    """``files.getUploadURLExternal``: the id of the file, for ``files.completeUploadExternal``."""


@dataclass(frozen=True)
class SlackMessage:
    """A message that was posted to Slack."""

    channel_id: str
    """The channel's id, e.g. ``C0123456789``, which file uploads need."""

    ts: str
    """The message's timestamp, e.g. ``1700000000.000100``: its id, and the ``thread_ts`` of replies in its thread."""


class SlackService(InfrastructureService):
    """The platform's messages to Slack."""

    service_name = InfrastructureServiceNames.SLACK
    error_class = SlackServiceError

    @abstractmethod
    def _api(self, method: str, payload: SlackPayloadType, form: bool = False) -> SlackApiResponse:
        """
        Call a Slack Web API method.

        :param method: The method, e.g. ``chat.postMessage``.
        :param payload: Its arguments.
        :param form: Send them form-encoded, rather than as JSON, which some methods, e.g.
            ``files.getUploadURLExternal``, require.
        :returns: Slack's response, whether or not it is ``ok``.
        :raises SlackServiceError: If Slack could not be reached, or did not respond with a Web API response.
        """

    @abstractmethod
    def _upload(self, upload_url: str, content: bytes) -> None:
        """
        Send a file's contents to the upload url that ``files.getUploadURLExternal`` returned.

        :param upload_url: The url.
        :param content: The file's contents.
        :raises SlackServiceError: If they could not be sent.
        """

    def _call(self, method: str, payload: SlackPayloadType, form: bool = False) -> SlackApiResponse:
        """
        Call a Slack Web API method, and raise unless it succeeded.

        :raises SlackServiceError: If it failed, with Slack's error, and the scope that the bot lacks, if any.
        """
        response = self._api(method, payload, form=form)
        if not response.ok:
            error = response.error or "unknown_error"
            if response.needed:
                error = f"{error} (the bot needs the scope {response.needed})"
            raise SlackServiceError(f"{method} failed: {error}")
        return response

    def log_not_sent(self, channel: str) -> None:
        """
        Log a message or file that was not posted because the service is not ready.

        :param channel: The channel it was for.
        """
        logger.warning("%s %s is not configured. Nothing was posted to %s.", self.formatted_class_name, self, channel)

    def post_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> Optional[SlackMessage]:
        """
        Post a message, formatted with Slack's ``mrkdwn``, without link or media previews.

        Failures are logged rather than raised, so that Slack never breaks the work that posts to it.

        :param channel: The channel's name, e.g. ``smarter``, or its id.
        :param text: The message, in ``mrkdwn``. Escape ``&``, ``<`` and ``>`` in text that is not
            markup, e.g. with :func:`escape`.
        :param thread_ts: The ``ts`` of a message to reply to, in its thread.
        :returns: The posted message, whose channel id and ``ts`` a reply or file upload needs, or
            None if it was not posted.
        """
        if not self.ready:
            self.log_not_sent(channel)
            return None
        payload: SlackPayloadType = {
            "channel": channel,
            "text": text,
            "mrkdwn": True,
            "unfurl_links": False,
            "unfurl_media": False,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts
        try:
            response = self._call("chat.postMessage", payload)
            if not response.channel or not response.ts:
                raise SlackServiceError("chat.postMessage returned no channel or ts")
        except SystemExit:
            raise
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s.post_message() could not post to %s: %s", self.formatted_class_name, channel, e)
            return None
        logger.info("%s.post_message() posted to %s", self.formatted_class_name, channel)
        return SlackMessage(channel_id=response.channel, ts=response.ts)

    # pylint: disable=too-many-arguments
    def upload_file(
        self,
        channel_id: str,
        filename: str,
        content: bytes,
        thread_ts: Optional[str] = None,
        initial_comment: str = "",
        title: Optional[str] = None,
    ) -> bool:
        """
        Upload a file to a channel, or to a message's thread.

        Uses Slack's upload flow: ``files.getUploadURLExternal``, then the file's contents to the
        url it returns, then ``files.completeUploadExternal``, which shares the file. The bot needs
        the scope ``files:write``. Failures are logged rather than raised.

        :param channel_id: The channel's id, e.g. :attr:`SlackMessage.channel_id`. Not its name.
        :param filename: The file's name, e.g. ``job.txt``.
        :param content: The file's contents.
        :param thread_ts: The ``ts`` of the message in whose thread to share the file.
        :param initial_comment: A message to post with the file.
        :param title: The file's title. By default, its name.
        :returns: True if the file was uploaded and shared.
        """
        if not self.ready:
            self.log_not_sent(channel_id)
            return False
        try:
            target = self._call("files.getUploadURLExternal", {"filename": filename, "length": len(content)}, form=True)
            if not target.upload_url or not target.file_id:
                raise SlackServiceError("files.getUploadURLExternal returned no upload_url or file_id")
            self._upload(target.upload_url, content)
            payload: SlackPayloadType = {
                "files": [{"id": target.file_id, "title": title or filename}],
                "channel_id": channel_id,
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts
            if initial_comment:
                payload["initial_comment"] = initial_comment
            self._call("files.completeUploadExternal", payload)
        except SystemExit:
            raise
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.upload_file() could not upload %s to %s: %s", self.formatted_class_name, filename, channel_id, e
            )
            return False
        logger.info(
            "%s.upload_file() uploaded %s (%s bytes) to %s",
            self.formatted_class_name,
            filename,
            len(content),
            channel_id,
        )
        return True


class SlackWebApiService(SlackService):
    """
    Slack, with the Slack Web API, as the bot of ``smarter_settings.slack_bot_token``.

    It is ready when the token is set. In the unit tests, it is never ready, unless
    ``allow_in_tests`` is True, so that tests never post to a real workspace.

    The token is sent only to :data:`SLACK_API_URL`, never to an upload url, and is never logged.
    Redirects are not followed.

    :param allow_in_tests: Post in the unit tests, e.g. with ``requests`` mocked.
    """

    def __init__(self, allow_in_tests: bool = False, **kwargs):
        super().__init__(provider_name="slack", **kwargs)
        self.allow_in_tests = allow_in_tests

    @property
    def ready(self) -> bool:
        if running_unit_tests() and not self.allow_in_tests:
            return False
        return smarter_settings.slack_bot_token is not None

    def _api(self, method: str, payload: SlackPayloadType, form: bool = False) -> SlackApiResponse:
        token = smarter_settings.slack_bot_token
        if token is None:
            raise SlackServiceError("smarter_settings.slack_bot_token is not configured")
        headers = {"Authorization": f"Bearer {token.get_secret_value()}"}
        if form:
            body: Union[SlackPayloadType, bytes] = payload
        else:
            headers["Content-Type"] = "application/json; charset=utf-8"
            body = json.dumps(payload).encode("utf-8")
        try:
            response = requests.post(
                f"{SLACK_API_URL}{method}", data=body, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=False
            )
        except requests.exceptions.RequestException as e:
            raise SlackServiceError(f"{method}: Slack could not be reached: {type(e).__name__}") from e
        if response.status_code != 200:
            raise SlackServiceError(f"{method}: Slack responded with HTTP {response.status_code}")
        try:
            return SlackApiResponse.model_validate(response.json())
        except ValueError as e:
            raise SlackServiceError(f"{method}: Slack's response is not a Web API response") from e

    def _upload(self, upload_url: str, content: bytes) -> None:
        url = urlparse(upload_url)
        host = (url.hostname or "").lower()
        if url.scheme != "https" or not (host == SLACK_UPLOAD_DOMAIN or host.endswith(f".{SLACK_UPLOAD_DOMAIN}")):
            raise SlackServiceError(f"the upload url is not a {SLACK_UPLOAD_DOMAIN} https url: {url.scheme}://{host}")
        try:
            response = requests.post(
                upload_url,
                data=content,
                headers={"Content-Type": "application/octet-stream"},
                timeout=UPLOAD_TIMEOUT,
                allow_redirects=False,
            )
        except requests.exceptions.RequestException as e:
            raise SlackServiceError(f"the upload could not reach Slack: {type(e).__name__}") from e
        if response.status_code != 200:
            raise SlackServiceError(f"the upload failed with HTTP {response.status_code}")


@dataclass
class PostedSlackMessage:
    """A message that :class:`InMemorySlackService` posted."""

    channel: str
    """The channel, as the caller named it."""

    channel_id: str
    text: str
    ts: str
    thread_ts: Optional[str] = None


@dataclass
class UploadedSlackFile:
    """A file that :class:`InMemorySlackService` uploaded."""

    channel_id: str
    filename: str
    title: str
    content: bytes
    thread_ts: Optional[str] = None
    initial_comment: str = ""


class InMemorySlackService(SlackService):
    """
    Slack in memory, for tests and local development: messages are kept in :attr:`messages`, and.

    files in :attr:`files`.

    A channel's id is its name, upper-cased, after a ``C``, e.g. ``CSMARTER``.

    :param ready: Whether the service is ready.
    """

    def __init__(self, ready: bool = True, **kwargs):
        super().__init__(provider_name="memory", **kwargs)
        self._ready = ready
        self.messages: list[PostedSlackMessage] = []
        self.files: list[UploadedSlackFile] = []
        self.errors: dict[str, str] = {}
        """Set a Web API method's error, e.g. ``{"files.getUploadURLExternal": "missing_scope"}``, to make it fail."""
        self._uploads: dict[str, tuple[str, Optional[bytes]]] = {}

    @property
    def ready(self) -> bool:
        return self._ready

    @staticmethod
    def channel_id(channel: str) -> str:
        """The id of a channel, by name or id."""
        return channel if channel.startswith("C") and channel.isupper() else f"C{channel.upper()}"

    def _api(self, method: str, payload: SlackPayloadType, form: bool = False) -> SlackApiResponse:
        if method in self.errors:
            return SlackApiResponse(ok=False, error=self.errors[method])
        if method == "chat.postMessage":
            channel = str(payload["channel"])
            ts = f"1700000000.{len(self.messages) + 1:06d}"
            thread_ts = payload.get("thread_ts")
            self.messages.append(
                PostedSlackMessage(
                    channel=channel,
                    channel_id=self.channel_id(channel),
                    text=str(payload["text"]),
                    ts=ts,
                    thread_ts=str(thread_ts) if thread_ts else None,
                )
            )
            return SlackApiResponse(ok=True, channel=self.channel_id(channel), ts=ts)
        if method == "files.getUploadURLExternal":
            file_id = f"F{len(self._uploads) + 1:08d}"
            self._uploads[file_id] = (str(payload["filename"]), None)
            return SlackApiResponse(ok=True, file_id=file_id, upload_url=f"https://files.slack.com/upload/v1/{file_id}")
        if method == "files.completeUploadExternal":
            files = payload.get("files")
            if not isinstance(files, list) or not files:
                return SlackApiResponse(ok=False, error="invalid_arguments")
            file_id = files[0]["id"]
            filename, content = self._uploads.get(file_id, ("", None))
            if content is None:
                return SlackApiResponse(ok=False, error="file_not_found")
            thread_ts = payload.get("thread_ts")
            self.files.append(
                UploadedSlackFile(
                    channel_id=str(payload["channel_id"]),
                    filename=filename,
                    title=files[0]["title"],
                    content=content,
                    thread_ts=str(thread_ts) if thread_ts else None,
                    initial_comment=str(payload.get("initial_comment", "")),
                )
            )
            return SlackApiResponse(ok=True)
        return SlackApiResponse(ok=False, error="unknown_method")

    def _upload(self, upload_url: str, content: bytes) -> None:
        file_id = upload_url.rsplit("/", 1)[-1]
        if file_id not in self._uploads:
            raise SlackServiceError(f"unknown upload url: {upload_url}")
        self._uploads[file_id] = (self._uploads[file_id][0], content)


def escape(text: str) -> str:
    """
    Escape the characters that Slack's ``mrkdwn`` reserves, ``&``, ``<`` and ``>``.

    Use it on text that is not markup, e.g. a log, so that it is shown as it is, and cannot
    mention people or channels, e.g. ``<!channel>``.

    :param text: The text.
    :returns: The text, escaped.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_slack_factory: Optional[Callable[[], SlackService]] = None
_slack: Optional[SlackService] = None


def configure_slack(factory: Optional[Callable[[], SlackService]]) -> None:
    """
    Set the factory of the Slack service that :func:`get_slack` returns.

    :param factory: Returns the service, or None to restore the default, :class:`SlackWebApiService`.
    """
    global _slack_factory, _slack  # pylint: disable=global-statement
    _slack_factory = factory
    _slack = None


def get_slack() -> SlackService:
    """Return the Slack service, which is created once."""
    global _slack  # pylint: disable=global-statement
    if _slack is None:
        _slack = _slack_factory() if _slack_factory is not None else SlackWebApiService()
    return _slack


__all__ = [
    "InMemorySlackService",
    "PostedSlackMessage",
    "SlackApiResponse",
    "SlackMessage",
    "SlackService",
    "SlackWebApiService",
    "UploadedSlackFile",
    "configure_slack",
    "escape",
    "get_slack",
]
