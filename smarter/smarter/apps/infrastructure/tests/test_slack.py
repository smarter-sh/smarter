"""
Test :mod:`smarter.apps.infrastructure.services.slack`.

Nothing is posted to Slack: the Web API service's ``requests.post`` is a fake, and the other tests
use the in-memory Slack service.
"""

import json
from unittest.mock import MagicMock, patch

import requests
from pydantic import SecretStr

from smarter.apps.infrastructure.exceptions import SlackServiceError
from smarter.apps.infrastructure.services import (
    InMemorySlackService,
    SlackMessage,
    SlackWebApiService,
    configure_slack,
    get_slack,
    infrastructure,
)
from smarter.apps.infrastructure.services.slack import SlackApiResponse, escape

from .base import InfrastructureTestBase

MODULE = "smarter.apps.infrastructure.services.slack"
TOKEN = "xoxb-test-token-not-real"
UPLOAD_URL = "https://files.slack.com/upload/v1/abc"


def slack_settings(token=SecretStr(TOKEN)) -> MagicMock:
    """Smarter_settings, with a Slack bot token."""
    return MagicMock(slack_bot_token=token)


def response(body=None, status_code: int = 200) -> MagicMock:
    """A fake requests.Response, whose json() is ``body``."""
    fake = MagicMock(status_code=status_code)
    if isinstance(body, Exception):
        fake.json.side_effect = body
    else:
        fake.json.return_value = body
    return fake


class TestEscape(InfrastructureTestBase):
    """Test escape()."""

    def test_escape(self):
        self.assertEqual(escape("a & b <!channel> c > d"), "a &amp; b &lt;!channel&gt; c &gt; d")


class TestConfigureSlack(InfrastructureTestBase):
    """Test configure_slack(), get_slack() and infrastructure.slack."""

    def test_default_is_web_api(self):
        configure_slack(None)
        self.assertIsInstance(get_slack(), SlackWebApiService)
        self.assertIs(get_slack(), get_slack())
        self.assertEqual(str(get_slack()), "slack.slack")

    def test_configured(self):
        slack = InMemorySlackService()
        configure_slack(lambda: slack)
        self.assertIs(infrastructure.slack, slack)


class TestInMemorySlackService(InfrastructureTestBase):
    """Test post_message() and upload_file(), with the in-memory Slack service."""

    def setUp(self):
        super().setUp()
        self.slack = InMemorySlackService()

    def test_post_message(self):
        message = self.slack.post_message("smarter", "*hello*")
        self.assertEqual(message, SlackMessage(channel_id="CSMARTER", ts="1700000000.000001"))
        reply = self.slack.post_message(message.channel_id, "reply", thread_ts=message.ts)
        self.assertEqual(reply.channel_id, "CSMARTER")
        self.assertEqual([m.text for m in self.slack.messages], ["*hello*", "reply"])
        self.assertIsNone(self.slack.messages[0].thread_ts)
        self.assertEqual(self.slack.messages[1].thread_ts, message.ts)

    def test_upload_file(self):
        self.assertTrue(
            self.slack.upload_file("CSMARTER", "job.txt", b"log\n", thread_ts="1.2", initial_comment="The log")
        )
        uploaded = self.slack.files[0]
        self.assertEqual(
            (uploaded.channel_id, uploaded.filename, uploaded.title, uploaded.content),
            ("CSMARTER", "job.txt", "job.txt", b"log\n"),
        )
        self.assertEqual((uploaded.thread_ts, uploaded.initial_comment), ("1.2", "The log"))
        self.assertTrue(self.slack.upload_file("CSMARTER", "job.txt", b"log", title="The job's log"))
        self.assertEqual(self.slack.files[1].title, "The job's log")
        self.assertIsNone(self.slack.files[1].thread_ts)

    def test_not_ready(self):
        slack = InMemorySlackService(ready=False)
        with patch(f"{MODULE}.logger") as logger:
            self.assertIsNone(slack.post_message("smarter", "hello"))
            self.assertFalse(slack.upload_file("CSMARTER", "job.txt", b"log"))
        self.assertEqual(logger.warning.call_count, 2)
        self.assertEqual((slack.messages, slack.files), ([], []))

    def test_post_failure_is_not_raised(self):
        self.slack.errors["chat.postMessage"] = "not_in_channel"
        with patch(f"{MODULE}.logger") as logger:
            self.assertIsNone(self.slack.post_message("smarter", "hello"))
        self.assertIn("not_in_channel", str(logger.error.call_args))

    def test_upload_failure_is_not_raised(self):
        """A bot without files:write can't upload: the error names the scope."""
        error = SlackApiResponse(ok=False, error="missing_scope", needed="files:write")
        with patch.object(self.slack, "_api", return_value=error), patch(f"{MODULE}.logger") as logger:
            self.assertFalse(self.slack.upload_file("CSMARTER", "job.txt", b"log"))
        self.assertIn("missing_scope (the bot needs the scope files:write)", str(logger.error.call_args))
        self.assertEqual(self.slack.files, [])

    def test_complete_failure_is_not_raised(self):
        self.slack.errors["files.completeUploadExternal"] = "channel_not_found"
        self.assertFalse(self.slack.upload_file("CNOPE", "job.txt", b"log"))
        self.assertEqual(self.slack.files, [])

    def test_missing_response_fields(self):
        """A response without the fields that the service needs is a failure."""
        with patch.object(self.slack, "_api", return_value=MagicMock(ok=True, channel=None, ts=None)):
            self.assertIsNone(self.slack.post_message("smarter", "hello"))
        with patch.object(self.slack, "_api", return_value=MagicMock(ok=True, upload_url=None, file_id=None)):
            self.assertFalse(self.slack.upload_file("CSMARTER", "job.txt", b"log"))

    def test_unknown_method_and_upload(self):
        # pylint: disable=protected-access
        self.assertEqual(self.slack._api("users.list", {}).error, "unknown_method")
        self.assertEqual(self.slack._api("files.completeUploadExternal", {"files": []}).error, "invalid_arguments")
        self.assertEqual(
            self.slack._api("files.completeUploadExternal", {"files": [{"id": "F1", "title": "x"}]}).error,
            "file_not_found",
        )
        with patch(f"{MODULE}.logger"):
            with patch.object(self.slack, "_upload", side_effect=ValueError("boom")):
                self.assertFalse(self.slack.upload_file("CSMARTER", "job.txt", b"log"))
        with self.assertRaises(SlackServiceError):
            self.slack._upload("https://files.slack.com/upload/v1/F99", b"log")

    def test_system_exit_is_raised(self):
        with patch.object(self.slack, "_api", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                self.slack.post_message("smarter", "hello")
            with self.assertRaises(SystemExit):
                self.slack.upload_file("CSMARTER", "job.txt", b"log")


class TestSlackWebApiService(InfrastructureTestBase):
    """Test SlackWebApiService, with requests.post faked."""

    def setUp(self):
        super().setUp()
        self.slack = SlackWebApiService(allow_in_tests=True)
        settings = patch(f"{MODULE}.smarter_settings", slack_settings())
        settings.start()
        self.addCleanup(settings.stop)
        post = patch(f"{MODULE}.requests.post")
        self.post = post.start()
        self.addCleanup(post.stop)

    def test_ready(self):
        self.assertTrue(self.slack.ready)
        self.assertFalse(SlackWebApiService().ready, "never ready in the unit tests")
        with patch(f"{MODULE}.smarter_settings", slack_settings(token=None)):
            self.assertFalse(self.slack.ready)

    def test_post_message(self):
        self.post.return_value = response({"ok": True, "channel": "C0123", "ts": "1.000100", "message": {}})
        message = self.slack.post_message("smarter", "*Done* &amp;", thread_ts="1.000001")
        self.assertEqual(message, SlackMessage(channel_id="C0123", ts="1.000100"))
        call = self.post.call_args
        self.assertEqual(call.args[0], "https://slack.com/api/chat.postMessage")
        self.assertEqual(call.kwargs["headers"]["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(call.kwargs["headers"]["Content-Type"], "application/json; charset=utf-8")
        self.assertFalse(call.kwargs["allow_redirects"])
        self.assertEqual(
            json.loads(call.kwargs["data"]),
            {
                "channel": "smarter",
                "text": "*Done* &amp;",
                "mrkdwn": True,
                "unfurl_links": False,
                "unfurl_media": False,
                "thread_ts": "1.000001",
            },
        )

    def test_upload_file(self):
        """The upload is three requests: get the upload url, send the file there, complete the upload."""
        self.post.side_effect = [
            response({"ok": True, "upload_url": UPLOAD_URL, "file_id": "F0123"}),
            response(None),
            response({"ok": True, "files": [{"id": "F0123"}]}),
        ]
        self.assertTrue(self.slack.upload_file("C0123", "job.txt", b"log\n", thread_ts="1.000100"))
        get_url, upload, complete = self.post.call_args_list
        self.assertEqual(get_url.args[0], "https://slack.com/api/files.getUploadURLExternal")
        self.assertEqual(get_url.kwargs["data"], {"filename": "job.txt", "length": 4})
        self.assertNotIn("Content-Type", get_url.kwargs["headers"])
        self.assertEqual(upload.args[0], UPLOAD_URL)
        self.assertEqual(upload.kwargs["data"], b"log\n")
        self.assertNotIn("Authorization", upload.kwargs["headers"], "the token is sent only to slack.com/api")
        self.assertEqual(complete.args[0], "https://slack.com/api/files.completeUploadExternal")
        self.assertEqual(
            json.loads(complete.kwargs["data"]),
            {"files": [{"id": "F0123", "title": "job.txt"}], "channel_id": "C0123", "thread_ts": "1.000100"},
        )

    def test_upload_url_must_be_slack(self):
        for url in ("http://files.slack.com/upload", "https://example.com/upload", "https://evilslack.com/upload"):
            with self.subTest(url=url):
                self.post.reset_mock()
                self.post.side_effect = [response({"ok": True, "upload_url": url, "file_id": "F0123"})]
                with patch(f"{MODULE}.logger") as logger:
                    self.assertFalse(self.slack.upload_file("C0123", "job.txt", b"log"))
                self.assertEqual(self.post.call_count, 1)
                self.assertIn("is not a slack.com https url", str(logger.error.call_args))

    def test_upload_failures(self):
        for side_effect, error in (
            (requests.exceptions.ConnectionError("down"), "could not reach Slack: ConnectionError"),
            (response(None, status_code=500), "failed with HTTP 500"),
        ):
            with self.subTest(error=error):
                self.post.side_effect = [
                    response({"ok": True, "upload_url": UPLOAD_URL, "file_id": "F0123"}),
                    side_effect,
                ]
                with patch(f"{MODULE}.logger") as logger:
                    self.assertFalse(self.slack.upload_file("C0123", "job.txt", b"log"))
                self.assertIn(error, str(logger.error.call_args))

    def test_api_failures(self):
        """Failures are logged, without the token, and never raised."""
        for side_effect, error in (
            (requests.exceptions.Timeout("slow"), "Slack could not be reached: Timeout"),
            (response({"ok": False}, status_code=429), "HTTP 429"),
            (response(ValueError("not json")), "not a Web API response"),
            (response({"ok": False, "error": "channel_not_found"}), "chat.postMessage failed: channel_not_found"),
            (response({"ok": False}), "unknown_error"),
        ):
            with self.subTest(error=error):
                self.post.side_effect = [side_effect]
                with patch(f"{MODULE}.logger") as logger:
                    self.assertIsNone(self.slack.post_message("smarter", "hello"))
                self.assertIn(error, str(logger.error.call_args))
                self.assertNotIn(TOKEN, str(logger.mock_calls))

    def test_token_removed(self):
        """The token is checked again when each request is sent."""
        with patch(f"{MODULE}.smarter_settings", slack_settings(token=None)):
            with patch.object(SlackWebApiService, "ready", True):
                with patch(f"{MODULE}.logger") as logger:
                    self.assertIsNone(self.slack.post_message("smarter", "hello"))
        self.assertIn("slack_bot_token is not configured", str(logger.error.call_args))
        self.post.assert_not_called()
