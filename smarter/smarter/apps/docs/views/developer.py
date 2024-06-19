# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.

"""
import os

import markdown
from django.shortcuts import render

from smarter.lib.django.view_helpers import SmarterWebView


# note: this is the path from the Docker container, not the GitHub repo.
DOCS_PATH = "/data/doc/"


# ------------------------------------------------------------------------------
# Public Access Base Views
# ------------------------------------------------------------------------------
class TxtBaseView(SmarterWebView):
    """Text base view"""

    template_path = "docs/txt_file.html"
    text_file: str = None
    title: str = None
    leader: str = None

    def get(self, request, *args, **kwargs):
        file_path = self.text_file
        with open(file_path, encoding="utf-8") as text_file:
            text_content = text_file.read()

        context = {
            "requirements_html": text_content,
            "title": self.title,
            "leader": self.leader,
        }
        return render(request, self.template_path, context=context)


class MarkdownBaseView(SmarterWebView):
    """Markdown base view"""

    template_path = "docs/markdown.html"
    markdown_file: str = None

    def get(self, request, *args, **kwargs):
        file_path = os.path.join(DOCS_PATH, self.markdown_file)
        with open(file_path, encoding="utf-8") as markdown_file:
            md_text = markdown_file.read()

        html = markdown.markdown(md_text)
        context = {
            "markdown_html": html,
        }

        return render(request, self.template_path, context=context)


# ------------------------------------------------------------------------------
# Public Access text file Views
# ------------------------------------------------------------------------------
class DeveloperDocsRequirementsView(TxtBaseView):
    """Developer docs base requirements view"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/smarter/requirements/base.txt"
        self.title = "Python Package Dependencies"
        self.leader = """
        Smarter Platform is a Python-Django micro-service application. Below is a list of the requirements and version
        pins for packages included in this environment.
        Note that we bump version pins on a monthly basis on the first of each month to our alpha branch. Version bumps
        follow the normal CI-CD workflow to arrive into
        the production environment, and that this takes an indertiminate amount of time before these ultimately arrive
        into the production environment.
        If you are developing your solution in Python then you can use this list to ensure that your development
        environment is in sync with the Smarter Platform.
        """


class DeveloperDocsDockerfileView(TxtBaseView):
    """Developer docs Dockerfile view"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/data/Dockerfile"
        self.title = "Dockerfile"
        self.leader = """
        Smarter Platform is a Docker-based Python-Django micro-service application that runs in Kubernetes. Below is
        the basic Dockerfile that is used to build the Smarter Platform Docker images for the application, the workers,
        and the celery-beat pods.
        """


class DeveloperDocsWeatherFunctionView(TxtBaseView):
    """Developer docs Weather function calling view"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/smarter/smarter/apps/chat/functions/function_weather.py"
        self.title = "function_weather.py"
        self.leader = """
        This is Smarter's implementation of the Python function 'get_current_weather()' referenced in
        OpenAI API 'Function Calling' documentation: https://platform.openai.com/docs/guides/function-calling which
        oddly, they neglected to implement.

        Smarter's documentation refers to this function repeatedly. It returns the current weather in a
        given location as a 24-hour forecast. The function is called by the OpenAI API 'function calling' feature
        and returns a JSON object.

        This example is foundational to how the Smarter platform implements its Plugin feature, which is an
        abstraction layer enabling non-programmers to achieve the same functionality as the Python function above,
        albeit with the functionality of their choice, and with the dynamically 'select' the Plugin to be presented
        to the LLM as a potential function to be called for a given prompt.

        This function uses the Google Maps API for geocoding and the Open-Meteo API for weather data.
        The Open-Meteo API is used to get the weather data. The API is rate-limited to 1 request per second. It is called with the
        openmeteo_requests Python package, which is a wrapper for the requests package. It is used to cache the API responses
        to avoid repeated API calls, and to retry failed API calls.
        """


class DeveloperDocsDockerComposeView(TxtBaseView):
    """Developer docs docker-compose.yml view"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/data/docker-compose.yml"
        self.title = "docker-compose.yml"
        self.leader = """
        Smarter Platform is a Docker-based Python-Django micro-service application that runs in Kubernetes. Below is
        a docker-compose.yml that strongly resembles the Kubernetes run-time configuration. You can use this file to
        synch your local development environment with the Smarter Platform.
        """


# ------------------------------------------------------------------------------
# Public Access Markdown Views
# ------------------------------------------------------------------------------
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
