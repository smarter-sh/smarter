"""Test scripts/pod_log_redact.py, which redacts credentials and personal data from downloaded logs."""

import collections
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pod_log_redact import main, redact


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
            self.assertEqual(output.getvalue().strip(), "redacted 1 file(s): email 1")

    def test_main_needs_a_folder(self):
        with (
            mock.patch.object(sys, "argv", ["pod_log_redact.py", "/no/such/folder"]),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
