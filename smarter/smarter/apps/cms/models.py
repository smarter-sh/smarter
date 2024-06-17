# pylint: disable=C0115
"""Wagtail page models for the CMS app."""

from django.db import models
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.snippets.models import register_snippet


@register_snippet
class RawHtmlSnippet(models.Model):
    name = models.CharField(verbose_name="Snippet Name", max_length=255)
    html = models.TextField(verbose_name="HTML Content")

    panels = [
        FieldPanel("name"),
        FieldPanel("html"),
    ]

    def __str__(self):
        return str(self.html)


class RawHtmlPage(Page):
    """Docs page model."""

    body = StreamField(
        [
            ("html", blocks.RawHTMLBlock()),
        ],
        null=True,
        blank=True,
    )
    sidebar = StreamField(
        [
            ("html_block", SnippetChooserBlock(RawHtmlSnippet)),
        ],
        null=True,
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
        FieldPanel("sidebar"),
    ]

    template = "cms/wagtail_base.html"
