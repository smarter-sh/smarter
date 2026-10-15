# pylint: disable=W0613
"""
Django REST framework views for the API admin app.

To-do:
 - import markdown, and render the markdown files in the /docs folder.
"""

from .base import MarkdownBaseView, TxtBaseView


# ------------------------------------------------------------------------------
# Public Access text file Views
# ------------------------------------------------------------------------------
class DeveloperDocsRequirementsView(TxtBaseView):
    """Developer docs base requirements view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/home/smarter_user/smarter/requirements/docker.txt"
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
    """Developer docs Dockerfile view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/home/smarter_user/data/Dockerfile"
        self.title = "Dockerfile"
        self.leader = """
        Smarter Platform is a Docker-based Python-Django micro-service application that runs in Kubernetes. Below is
        the basic Dockerfile that is used to build the Smarter Platform Docker images for the application, the workers,
        and the celery-beat pods.
        """


class DeveloperDocsMakefileView(TxtBaseView):
    """Developer docs Makefile view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/home/smarter_user/data/Makefile"
        self.title = "Makefile"
        self.leader = """
        This is the Makefile for https://github.com/smarter-sh/smarter which you can use as a reference
        to for how what version of Python we are using, and how we
        initialize our local development environments.
        """


class DeveloperDocsExtensionProtocolView(TxtBaseView):
    """Developer docs Smarter Extension tool protocol view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/home/smarter_user/smarter/smarter/apps/llmtool/extension/protocol.py"
        self.title = "llmtool/extension/protocol.py"
        self.leader = """
        This is the protocol that the tools of a Smarter Extension implement. An Extension is an
        installable Python package that adds tools to the LLMs of a Smarter platform, through the
        function calling feature of OpenAI-compatible APIs:
        https://platform.openai.com/docs/guides/function-calling.

        A tool declares its name and the Pydantic model of its arguments, and implements call().
        The platform generates the tool's definition for the LLM, validates the LLM's arguments,
        runs the tool with a timeout, and returns its result, or its error, to the LLM. The
        official weather extension, https://github.com/smarter-sh/smarter-extension-weather, is
        the reference implementation.
        """


class DeveloperDocsDockerComposeView(TxtBaseView):
    """Developer docs docker-compose.yml view."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.text_file = "/home/smarter_user/data/docker-compose.yml"
        self.title = "docker-compose.yml"
        self.leader = """
        Smarter Platform is a Docker-based Python-Django micro-service application that runs in Kubernetes. Below is
        a docker-compose.yml that strongly resembles the Kubernetes run-time configuration. You can use this file to
        synch your local development environment with the Smarter Platform.
        """


# ------------------------------------------------------------------------------
# Public Access Markdown Views
# ------------------------------------------------------------------------------


class DeveloperDocsReadme(MarkdownBaseView):
    """Developer README.md view."""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "README.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsChangelog(MarkdownBaseView):
    """Developer CHANGELOG.md view."""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "CHANGELOG.md"
        return super().dispatch(request, *args, **kwargs)


class DeveloperDocsCodeOfConduct(MarkdownBaseView):
    """Developer CODE_OF_CONDUCT.md view."""

    def dispatch(self, request, *args, **kwargs):
        self.markdown_file = "CODE_OF_CONDUCT.md"
        return super().dispatch(request, *args, **kwargs)
