# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
import logging
import os

import markdown
from django.shortcuts import render

from smarter.lib.django.view_helpers import SmarterNeverCachedWebView, SmarterWebView


logger = logging.getLogger(__name__)

DOCS_PATH = "/data/doc/"


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------


class DocsView(SmarterWebView):
    """/api/docs/ landing page view"""

    template_path = "api/docs/index.html"


class SiteMapView(SmarterNeverCachedWebView):
    """/api/docs/sitemap/ Keen sample page view"""

    template_path = "api/docs/sitemap.html"


class MarkdownBaseView(SmarterWebView):
    """Markdown base view"""

    template_path = "api/docs/markdown.html"
    markdown_file: str = None

    def get(self, request, *args, **kwargs):
        file_path = os.path.join(DOCS_PATH, self.markdown_file)
        with open(file_path, encoding="utf-8") as markdown_file:
            md_text = markdown_file.read()

        html = markdown.markdown(md_text)

        return render(request, self.template_path, {"markdown_html": html})


class DeveloperDocsTwelveFactorView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "12-FACTOR.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsArchitectureView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "ARCHITECTURE.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsChatBotApiView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "CHATBOT_API.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsCliView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "CLI.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsDjangoReactView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "DJANGO-REACT-INTEGRATION.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsGoodCodoingPracticeView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "GOOD_CODING_PRACTICE.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsOpenAIGettingStartedView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "OPENAI_API_GETTING_STARTED_GUIDE.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsSemanticVersioningView(MarkdownBaseView):
    """Developer docs 12-factor view"""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "SEMANTIC_VERSIONING.md"
        return super().dispatch(request, *args, **kwargs)
