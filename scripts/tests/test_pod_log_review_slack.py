"""Test scripts/pod_log_review_slack.py, which tells Slack what the pod log review did."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import pod_log_review_slack
from pod_log_review_slack import (
    ACTION_LABELS,
    actions,
    clean_bill_of_health,
    escape,
    main,
)
from pod_log_review_stream import WRITE_TOOLS, PodInventory
from tests.pod_log_fixtures import (
    result_event,
    write_call,
    write_log_dir,
    write_result,
    write_stream,
)

ISSUE_URL = "https://github.com/smarter-sh/smarter/issues/12"
CLOSED = [
    write_call("close_issue", "t1"),
    write_result(f"Closed issue #12 in smarter-sh/smarter by bot: x\n{ISSUE_URL}", "t1"),
]


class TestPodLogReviewSlack(unittest.TestCase):
    """Test the message, and when it is posted."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.log_dir = write_log_dir(self.root)

    def main(self, events: list, *flags: str, token: str = "") -> tuple[int, str, mock.Mock]:
        """
        Run main() on a stream of these events.

        :returns: Its exit status, what it printed, and the mock of ``post()``.
        """
        stream = write_stream(self.root / "stream.jsonl", events)
        argv = ["pod_log_review_slack.py", stream, "--channel", "smarter", "--title", "Pod log review"]
        argv += ["--run-url", "https://example.com/run", "--log-dir", self.log_dir, "--since", "25h", *flags]
        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict("os.environ", {"SLACK_BOT_TOKEN": token}),
            mock.patch.object(pod_log_review_slack, "post") as post,
            redirect_stdout(output),
            redirect_stderr(output),
        ):
            status = main()
        return status, output.getvalue(), post

    def test_a_run_that_wrote_lists_its_writes(self):
        status, output, _ = self.main([*CLOSED, result_event()], "--dry-run")
        self.assertEqual(status, 0)
        self.assertIn(f":white_check_mark: Closed issue #12 in smarter-sh/smarter: x <{ISSUE_URL}|view>", output)
        self.assertNotIn("Clean bill of health", output)

    def test_a_healthy_run_gets_a_clean_bill_of_health(self):
        status, output, _ = self.main([result_event()], "--dry-run")
        self.assertEqual(status, 0)
        self.assertIn("*Clean bill of health!* Claude read the last 25h of logs", output)
        self.assertIn("4 pod(s) up and running (smarter 2, smarter-beat 1, smarter-worker 1)", output)
        self.assertIn(":muscle: Zero restarts", output)
        self.assertIn(":package: Release v0.40.4", output)

    def test_a_healthy_verdict_with_redactions_posts_nothing(self):
        (Path(self.log_dir) / "redactions.json").write_text('{"total": 1}', encoding="utf-8")
        status, output, post = self.main([result_event()], token="xoxb-test")
        self.assertEqual(status, 0)
        self.assertIn("nothing is posted", output)
        post.assert_not_called()

    def test_other_runs_post_nothing(self):
        cases = {
            "needs attention": [result_event("Verdict: needs attention")],
            "error": [result_event("Verdict: healthy", is_error=True)],
            "free text after the verdict": [result_event("Verdict: healthy, but look")],
            "did not finish": [{"type": "system"}],
        }
        for name, events in cases.items():
            with self.subTest(name):
                status, output, post = self.main(events, token="xoxb-test")
                self.assertEqual(status, 0)
                self.assertIn("nothing is posted", output)
                post.assert_not_called()

    def test_a_failed_write_is_not_listed(self):
        events = [write_call("create_issue", "t1"), write_result("GitHub refused it", "t1", is_error=True)]
        self.assertEqual(actions(write_stream(self.root / "s.jsonl", events)), [])

    def test_posts_with_the_token(self):
        status, output, post = self.main([*CLOSED], token="xoxb-test")
        self.assertEqual(status, 0)
        self.assertIn("posted to smarter", output)
        channel, text, token = post.call_args.args
        self.assertEqual((channel, token), ("smarter", "xoxb-test"))
        self.assertIn(ISSUE_URL, text)

    def test_without_a_token_nothing_is_posted(self):
        status, output, post = self.main([*CLOSED])
        self.assertEqual(status, 0)
        self.assertIn("SLACK_BOT_TOKEN is not set", output)
        post.assert_not_called()

    def test_a_refusal_fails(self):
        stream = write_stream(self.root / "stream.jsonl", CLOSED)
        argv = ["pod_log_review_slack.py", stream, "--channel", "smarter", "--title", "T"]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}),
            mock.patch.object(pod_log_review_slack, "post", side_effect=RuntimeError("not_in_channel")),
            redirect_stdout(io.StringIO()),
            redirect_stderr(io.StringIO()) as errors,
        ):
            self.assertEqual(main(), 1)
        self.assertIn("not_in_channel", errors.getvalue())

    def test_a_missing_stream_fails(self):
        argv = ["pod_log_review_slack.py", str(self.root / "missing.jsonl"), "--channel", "c", "--title", "T"]
        with mock.patch.object(sys, "argv", argv), redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)

    def test_clean_bill_of_health_leaves_out_what_it_lacks(self):
        text = clean_bill_of_health("T", PodInventory(restarts=2), "", "")
        self.assertIn("Claude read every log", text)
        self.assertIn("2 restart(s)", text)
        self.assertNotIn("pods up", text)
        self.assertNotIn("Release", text)
        self.assertTrue(text.endswith("written by Claude Code"))

    def test_every_write_tool_has_a_label(self):
        self.assertEqual(set(ACTION_LABELS), set(WRITE_TOOLS))

    def test_escape(self):
        self.assertEqual(escape("<@here> & co"), "&lt;@here&gt; &amp; co")


if __name__ == "__main__":
    unittest.main()
