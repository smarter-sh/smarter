"""Wagtail page models for the CMS app."""

from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class DocsPage(Page):
    """Docs page model."""

    body = StreamField(
        [
            ("html", blocks.RawHTMLBlock()),
        ],
        null=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    template = "cms/base.html"
