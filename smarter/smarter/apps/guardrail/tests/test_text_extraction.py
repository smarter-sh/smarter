"""
Test :mod:`smarter.apps.guardrail.services.text_extraction`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.guardrail.services.text_extraction import (
    extract_segments,
    latest_user_message_index,
    read_segment,
    resolve_path,
    tokenize,
    write_segment,
)
from smarter.apps.provider.services.text_completion.contracts import GuardrailStage
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import input_payload, output_payload


class TestTextExtraction(SmarterTestBase):
    """Test the extraction, reading and writing of the text that guardrails scan."""

    def test_pre_scans_only_the_latest_user_message(self):
        """Test that input guardrails scan the latest user message, not the system prompt nor the history."""
        payload = input_payload(
            "the new message",
            history=[{"role": "user", "content": "an old message"}, {"role": "assistant", "content": "a reply"}],
        )
        payload["messages"].append({"role": "smarter", "content": "an internal message"})
        segments = extract_segments(payload, GuardrailStage.PRE)
        self.assertEqual([(s.path, s.text) for s in segments], [("messages[3].content", "the new message")])

    def test_pre_without_user_message(self):
        """Test a request without a user message."""
        self.assertEqual(extract_segments({"messages": [{"role": "system", "content": "x"}]}, GuardrailStage.PRE), [])
        self.assertEqual(extract_segments({}, GuardrailStage.PRE), [])
        self.assertIsNone(latest_user_message_index([]))

    def test_pre_content_parts(self):
        """Test that the text parts of a multi-part message are scanned."""
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "look at this"},
                        {"type": "image_url", "image_url": {"url": "https://example.com/a.png"}},
                        {"type": "text", "text": "and this"},
                    ],
                }
            ]
        }
        segments = extract_segments(payload, GuardrailStage.PRE)
        self.assertEqual([s.path for s in segments], ["messages[0].content[0].text", "messages[0].content[2].text"])

    def test_post(self):
        """Test that output guardrails scan each choice's content, and refusal."""
        payload = output_payload("a reply")
        payload["choices"].append({"index": 1, "message": {"role": "assistant", "content": None, "refusal": "no"}})
        segments = extract_segments(payload, GuardrailStage.POST)
        self.assertEqual(
            [(s.path, s.text) for s in segments],
            [("choices[0].message.content", "a reply"), ("choices[1].message.refusal", "no")],
        )

    def test_read_and_write(self):
        """Test that write_segment returns a changed copy, and leaves the original unchanged."""
        payload = input_payload("secret")
        updated = write_segment(payload, "messages[1].content", "[REDACTED]")
        self.assertEqual(read_segment(updated, "messages[1].content"), "[REDACTED]")
        self.assertEqual(read_segment(payload, "messages[1].content"), "secret")
        self.assertEqual(write_segment(payload, "messages[9].content", "x"), payload)
        self.assertIsNone(read_segment(payload, "messages[9].content"))
        self.assertIsNone(read_segment(payload, "messages"))

    def test_paths(self):
        """Test tokenize and resolve_path."""
        self.assertEqual(tokenize("messages[3].content[0].text"), ["messages", 3, "content", 0, "text"])
        self.assertEqual(tokenize("choices[0].message.content"), ["choices", 0, "message", "content"])
        self.assertEqual(resolve_path({}, ""), (None, None))
