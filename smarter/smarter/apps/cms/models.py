"""Wagtail page models for the CMS app."""

from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page


class CustomHTMLBlock(blocks.RichTextBlock):
    """Custom HTML block with bold, italic, and link features."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs, features=["html", "bold", "italic", "link"])


class DocsPage(Page):
    """Home page model."""

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

    template = "cms/home_page.html"
