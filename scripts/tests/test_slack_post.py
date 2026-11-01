"""
Tests of scripts/slack_post.py, which posts the workflows' messages to Slack.

They need only the standard library, and never call Slack. Run them from the repository's root:

    python -m unittest discover -s scripts/tests
"""

import importlib.util
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "slack_post.py"
spec = importlib.util.spec_from_file_location("slack_post", SCRIPT_PATH)
slack_post = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slack_post)


def run(argv, stdin, environ):
    """Run main() with this stdin and environment.

    Returns (exit code, stdout, stderr).
    """
    out, err = io.StringIO(), io.StringIO()
    with (
        mock.patch("sys.stdin", io.StringIO(stdin)),
        mock.patch("sys.stderr", err),
        mock.patch.dict("os.environ", environ, clear=True),
        redirect_stdout(out),
    ):
        code = slack_post.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestMain(unittest.TestCase):
    """Main() posts stdin, only with a token and a message."""

    def test_dry_run_prints(self):
        with mock.patch.object(slack_post, "post") as post:
            code, out, _ = run(["--channel", "smarter", "--dry-run"], "*hello*\n", {"SLACK_BOT_TOKEN": "xoxb-test"})
        self.assertEqual((code, out), (0, "*hello*\n"))
        post.assert_not_called()

    def test_no_token_posts_nothing(self):
        with mock.patch.object(slack_post, "post") as post:
            code, out, _ = run(["--channel", "smarter"], "hello", {})
        self.assertEqual(code, 0)
        self.assertIn("SLACK_BOT_TOKEN is not set", out)
        post.assert_not_called()

    def test_empty_message_posts_nothing(self):
        with mock.patch.object(slack_post, "post") as post:
            code, out, _ = run(["--channel", "smarter"], "  \n", {"SLACK_BOT_TOKEN": "xoxb-test"})
        self.assertEqual(code, 0)
        self.assertIn("empty", out)
        post.assert_not_called()

    def test_posts_with_the_token(self):
        with mock.patch.object(slack_post, "post") as post:
            code, out, _ = run(["--channel", "smarter"], "hello\n", {"SLACK_BOT_TOKEN": "xoxb-test"})
        self.assertEqual(code, 0)
        post.assert_called_once_with("smarter", "hello", "xoxb-test")
        self.assertNotIn("xoxb-test", out)

    def test_slack_refuses(self):
        with mock.patch.object(
            slack_post, "post", side_effect=RuntimeError("Slack refused the message: not_in_channel")
        ):
            code, _, err = run(["--channel", "smarter"], "hello", {"SLACK_BOT_TOKEN": "xoxb-test"})
        self.assertEqual(code, 1)
        self.assertIn("not_in_channel", err)


class TestPost(unittest.TestCase):
    """Post() sends chat.postMessage, and raises when Slack refuses."""

    def response(self, body: bytes):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = body
        return response

    def test_sends_the_request(self):
        with mock.patch("urllib.request.urlopen", return_value=self.response(b'{"ok": true}')) as urlopen:
            slack_post.post("smarter", "hello", "xoxb-test")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, slack_post.SLACK_POST_MESSAGE_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer xoxb-test")
        self.assertEqual(
            json.loads(request.data),
            {"channel": "smarter", "text": "hello", "unfurl_links": False, "unfurl_media": False},
        )

    def test_unfurl_and_answer(self):
        body = b'{"ok": true, "channel": "C1", "ts": "1.2"}'
        with mock.patch("urllib.request.urlopen", return_value=self.response(body)) as urlopen:
            answer = slack_post.post("C1", "<https://blog.smarter.sh/x/|x>", "xoxb-test", unfurl=True)
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual((sent["unfurl_links"], sent["unfurl_media"]), (True, True))
        self.assertEqual((answer["channel"], answer["ts"]), ("C1", "1.2"))

    def test_raises_when_refused(self):
        body = b'{"ok": false, "error": "not_in_channel"}'
        with mock.patch("urllib.request.urlopen", return_value=self.response(body)):
            with self.assertRaisesRegex(RuntimeError, "not_in_channel"):
                slack_post.post("smarter", "hello", "xoxb-test")


if __name__ == "__main__":
    unittest.main()
