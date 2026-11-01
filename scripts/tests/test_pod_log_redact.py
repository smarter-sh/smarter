"""Test scripts/pod_log_redact.py, which redacts credentials and personal data from downloaded logs."""

import collections
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pod_log_redact import REPORT_NAME, locate, main, read_report, redact


class TestPodLogRedact(unittest.TestCase):
    """Test redact() and main()."""

    def test_redact(self):
        counts: collections.Counter = collections.Counter()
        text = redact(
            "user someone@example.com password=hunter22 from 8.8.8.8 via 10.0.0.1 at 14:04:45 on 127.0.0.1",
            counts,
        )
        self.assertNotIn("someone@example.com", text)
        self.assertNotIn("hunter22", text)
        self.assertIn("password=<redacted:secret>", text)
        self.assertIn("<redacted:ip-address>", text)
        self.assertIn("10.0.0.1", text, "a private address is kept")
        self.assertIn("14:04:45", text, "a time is not an address")
        self.assertIn("127.0.0.1", text)
        self.assertEqual(counts, {"email": 1, "secret": 1, "ip-address": 1})

    def test_main_rewrites_logs_in_place(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / "smarter" / "pod.log"
            log.parent.mkdir()
            log.write_text("mail someone@example.com\n", encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["pod_log_redact.py", folder]), redirect_stdout(output):
                self.assertEqual(main(), 0)
            self.assertEqual(log.read_text(encoding="utf-8"), "mail <redacted:email>\n")
            first, warning = output.getvalue().strip().splitlines()
            self.assertEqual(first, "redacted 1 file(s): email 1")
            self.assertTrue(warning.startswith("::warning::1 redaction(s) in 1 log(s)"))
            self.assertNotIn("someone", output.getvalue())
            report = json.loads((Path(folder) / REPORT_NAME).read_text(encoding="utf-8"))
            self.assertEqual(
                report,
                {
                    "total": 1,
                    "kinds": {"email": 1},
                    "files": {"smarter/pod.log": {"email": {"count": 1, "lines": [1]}}},
                },
            )
            self.assertNotIn("someone", json.dumps(report), "the report never holds a value")
            # a second run reports the placeholders that are already there, the same way.
            with mock.patch.object(sys, "argv", ["pod_log_redact.py", folder]), redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            self.assertEqual(read_report(folder), report)

    def test_main_reports_nothing_on_clean_logs(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "pod.log").write_text("all is well\n", encoding="utf-8")
            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["pod_log_redact.py", folder]), redirect_stdout(output):
                self.assertEqual(main(), 0)
            self.assertEqual(output.getvalue().strip(), "redacted 1 file(s): nothing")
            self.assertEqual(read_report(folder), {"total": 0, "kinds": {}, "files": {}})

    def test_locate(self):
        text = "a\n<redacted:email> and <redacted:email>\nb <redacted:token>\n" + "<redacted:email>\n" * 30
        found = locate(text)
        self.assertEqual(found["token"], {"count": 1, "lines": [3]})
        self.assertEqual(found["email"]["count"], 32)
        self.assertEqual(found["email"]["lines"][:2], [2, 4], "a line is listed once")
        self.assertEqual(len(found["email"]["lines"]), 20)
        self.assertEqual(locate("nothing here"), {})

    def test_read_report_without_a_report(self):
        self.assertEqual(read_report(""), {})
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(read_report(folder), {})
            (Path(folder) / REPORT_NAME).write_text("not json", encoding="utf-8")
            self.assertEqual(read_report(folder), {})
            (Path(folder) / REPORT_NAME).write_text("[1]", encoding="utf-8")
            self.assertEqual(read_report(folder), {})

    def test_main_needs_a_folder(self):
        with (
            mock.patch.object(sys, "argv", ["pod_log_redact.py", "/no/such/folder"]),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
