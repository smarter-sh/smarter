"""
The emails of the doodle app.

- :func:`email_drawn_doodle` tells the platform's admin, ``smarter_settings.platform_email_admin``,
  that the Smarter Doodle Artist drew new artwork for a region's doodle, with a link to the doodle
  in the Django admin, where a superuser approves it while the ``enable_doodle_auto_approve`` switch
  is off. :func:`smarter.apps.doodle.editor.apply_decision` sends it once per drawing: a doodle
  whose artwork was drawn on an earlier run is not sent again.
"""

import html

from django.urls import reverse

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.infrastructure.services import infrastructure
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .caching import artwork_url
from .models import Doodle, DoodleStatus
from .regions import DoodleRegion

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING])


def absolute_url(path: str) -> str:
    """
    Return a path of the platform as an absolute url, for an email.

    :param path: e.g. ``/api/v1/doodles/artwork/<sha256>.svg``.
    :returns: e.g. ``https://platform.example.com/api/v1/doodles/artwork/<sha256>.svg``.
    :rtype: str
    """
    url = f"{smarter_settings.environment_url}{path}"
    return url


def drawn_doodle_subject(doodle: Doodle) -> str:
    """
    Return the subject of the email about a drawn doodle.

    :param doodle: The doodle.
    :returns: e.g. ``The Smarter Doodle Artist drew Revolution Day for Mexico, 2035-11-19``.
    :rtype: str
    """
    region = DoodleRegion(doodle.region).label
    subject = f"The Smarter Doodle Artist drew {doodle.title} for {region}, {doodle.date.isoformat()}"
    return subject


def drawn_doodle_body(doodle: Doodle) -> str:
    """
    Return the HTML body of the email about a drawn doodle.

    Every value is escaped: the title, caption and reason come from an LLM.

    :param doodle: The doodle.
    :returns: The HTML.
    :rtype: str
    """
    region = DoodleRegion(doodle.region).label
    status = DoodleStatus(doodle.status).label
    image = absolute_url(artwork_url(doodle.artwork.sha256))
    admin_path = reverse(f"{smarter_restricted_admin_site.name}:doodle_doodle_change", args=[doodle.pk])
    admin = absolute_url(admin_path)
    lines = [
        f"<p>The Smarter Doodle Artist drew a new doodle for {html.escape(str(region))}, "
        f"on {doodle.date.isoformat()}.</p>",
        f'<p><img src="{html.escape(image)}?still=1" alt="{html.escape(doodle.alt_text)}" width="520"></p>',
        "<ul>",
        f"<li>Title: {html.escape(doodle.title)}</li>",
        f"<li>Caption: {html.escape(doodle.caption)}</li>",
        f"<li>Status: {html.escape(str(status))}</li>",
    ]
    if doodle.link_url:
        link = html.escape(doodle.link_url)
        lines.append(f'<li>Link: <a href="{link}">{link}</a></li>')
    lines.append(f"<li>Why: {html.escape(doodle.reason)}</li>")
    lines.append("</ul>")
    if doodle.status == DoodleStatus.PROPOSED:
        lines.append(f'<p>It is shown once a superuser approves it: <a href="{html.escape(admin)}">review it</a>.</p>')
    else:
        lines.append(f'<p><a href="{html.escape(admin)}">See it in the admin</a>.</p>')
    body = "\n".join(lines)
    return body


def email_drawn_doodle(doodle: Doodle) -> bool:
    """
    Email the platform's admin that the Smarter Doodle Artist drew new artwork for a doodle.

    :param doodle: The doodle, saved, with its drawn theme and artwork.
    :returns: True if the email was sent. False, e.g., when email isn't configured.
    :rtype: bool
    """
    subject = drawn_doodle_subject(doodle)
    body = drawn_doodle_body(doodle)
    to = str(smarter_settings.platform_email_admin)
    sent = infrastructure.email.send_email(subject=subject, body=body, to=to, html=True, bcc_admin=False)
    logger.info("emailed the admin about the doodle %s: %s.", doodle.pk, sent)
    return sent


__all__ = ["email_drawn_doodle"]
