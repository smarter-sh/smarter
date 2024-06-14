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
    """Home page model.
    path("api/", DocsApiView.as_view(), name="docs_api"),
    path("cli/", DocsCliView.as_view(), name="docs_cli"),
    path("developers/", DocsDevelopersView.as_view(), name="docs_developers"),
    path("learn/", DocsLearnView.as_view(), name="docs_learn"),
    path("json-schemas/", DocsJsonSchemasView.as_view(), name="docs_json_schemas"),
    path("manifests/", DocsManifestsView.as_view(), name="docs_manifests"),
    path("plugins/", DocsPluginsView.as_view(), name="docs_plugins"),
    path("sitemap", SiteMapView.as_view(), name="sitemap"),
    path("developer/", DeveloperDocsTwelveFactorView.as_view(), name="developer-12-factor"),
    """

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
