"""
Test :mod:`smarter.apps.doodle.notifications`, the email to the admin about a drawn doodle.

The email service is patched, so nothing is sent: each test reads what would have been.
"""

from unittest.mock import patch

from smarter.apps.doodle import notifications
from smarter.apps.doodle.models import Doodle, DoodleSource, DoodleStatus
from smarter.apps.doodle.notifications import email_drawn_doodle
from smarter.common.conf import smarter_settings

from .mixins import QUIET_DAY, DoodleTestMixin


class TestDoodleNotifications(DoodleTestMixin):
    """The admin is told what was drawn, for which region and day, and where to approve it."""

    def setUp(self):
        super().setUp()
        self.addCleanup(self.delete_doodles, QUIET_DAY)
        theme = self.theme("diwali")
        self.doodle = Doodle.objects.create(
            date=QUIET_DAY,
            region="mx",
            theme=theme,
            artwork=theme.artwork,
            status=DoodleStatus.PROPOSED,
            source=DoodleSource.LLM,
            title="Fiesta <b>Day</b>",
            caption="Happy Fiesta Day!",
            alt_text='Paper flags "hang" above a Smarter LLMClient.',
            link_url="https://en.wikipedia.org/wiki/Fiesta",
            reason="Chosen by the Smarter Doodle Editor, and drawn by the Smarter Doodle Artist: a fun day.",
        )

    def send(self, doodle: Doodle):
        """Email about a doodle, and return the call to the email service."""
        with patch.object(notifications, "infrastructure") as infrastructure:
            infrastructure.email.send_email.return_value = True
            sent = email_drawn_doodle(doodle)
        self.assertTrue(sent)
        infrastructure.email.send_email.assert_called_once()
        return infrastructure.email.send_email.call_args.kwargs

    def test_email_of_a_proposed_doodle(self):
        email = self.send(self.doodle)
        self.assertEqual(email["to"], str(smarter_settings.platform_email_admin))
        self.assertTrue(email["html"])
        self.assertFalse(email["bcc_admin"])
        self.assertEqual(email["subject"], "The Smarter Doodle Artist drew Fiesta <b>Day</b> for Mexico, 2035-11-03")
        body = email["body"]
        # what an LLM wrote is escaped
        self.assertIn("Fiesta &lt;b&gt;Day&lt;/b&gt;", body)
        self.assertIn("Paper flags &quot;hang&quot;", body)
        self.assertNotIn("<b>Day</b>", body)
        self.assertIn(f"{smarter_settings.environment_url}/api/v1/doodles/artwork/", body)
        self.assertIn(".svg?still=1", body)
        self.assertIn(f"/doodle/doodle/{self.doodle.pk}/change/", body)
        self.assertIn("Proposed, awaiting approval", body)
        self.assertIn("review it", body)
        self.assertIn('href="https://en.wikipedia.org/wiki/Fiesta"', body)

    def test_email_of_an_approved_doodle(self):
        Doodle.objects.filter(pk=self.doodle.pk).update(status=DoodleStatus.APPROVED, link_url="")
        self.doodle.refresh_from_db()
        body = self.send(self.doodle)["body"]
        self.assertIn("See it in the admin", body)
        self.assertNotIn("review it", body)
        self.assertNotIn("Link:", body)

    def test_email_is_not_sent_without_email(self):
        with patch.object(notifications, "infrastructure") as infrastructure:
            infrastructure.email.send_email.return_value = False
            self.assertFalse(email_drawn_doodle(self.doodle))
