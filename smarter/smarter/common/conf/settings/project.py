# pylint: disable=no-member,no-self-argument,unused-argument,R0801
"""Read-only facts about the running software: versions, project urls and paths."""

import os
from functools import cached_property
from typing import List

from pydantic import BaseModel

from smarter.common.conf.const import DOT_ENV_LOADED
from smarter.common.const import (
    SMARTER_API_KEY_MAX_LIFETIME_DAYS,
    SMARTER_PROJECT_CDN_URL,
    SMARTER_PROJECT_DOCS_URL,
    SMARTER_PROJECT_WEBSITE_URL,
)
from smarter.common.utils import get_repository_url, get_semantic_version


class ProjectSettings(BaseModel):
    """Facts about the running software: versions, urls of the Smarter project, and paths."""

    @cached_property
    def smarter_project_website_url(self) -> str:
        """
        Return the URL for the Smarter project website.

        Example:
            >>> print(smarter_settings.smarter_project_website_url)
            https://www.smarter.sh
        """
        return SMARTER_PROJECT_WEBSITE_URL

    @cached_property
    def smarter_project_cdn_url(self) -> str:
        """
        Return the URL for the Smarter project CDN.

        Example:
            >>> print(smarter_settings.smarter_project_cdn_url)
            https://cdn.smarter.sh
        """
        return SMARTER_PROJECT_CDN_URL

    @cached_property
    def smarter_project_docs_url(self) -> str:
        """
        Return the URL for the Smarter project documentation.

        Example:
            >>> print(smarter_settings.smarter_project_docs_url)
            https://docs.smarter.sh
        """
        return SMARTER_PROJECT_DOCS_URL

    @property
    def data_directory(self) -> str:
        """
        Return the path to the data directory:

        Example:
            >>> print(smarter_settings.data_directory)
            '/home/smarter_user/data'

        Note:
            This is based on the Dockerfile located in the root of the repository.
            See https://github.com/smarter-sh/smarter/blob/main/Dockerfile
        """
        return "/home/smarter_user/data"

    @property
    def is_using_dotenv_file(self) -> bool:
        """
        Indicates whether a `.env` file was loaded for this instance of smarter_settings.

        Returns:
            bool: True if a `.env` file was loaded, False otherwise.

        Example:
            >>> print(smarter_settings.is_using_dotenv_file)
            True

        Note:
            This property reflects the state at the time the settings object was created.
            It would gemnerally only be expected to be True in local development environments.

        See Also:
            - DOT_ENV_LOADED
        """
        return DOT_ENV_LOADED

    @cached_property
    def environment_variables(self) -> List[str]:
        """
        Lists all environment variables.

        Returns:
            List[str]: A list of the environment variable names currently set in the OS environment
                in which the application is running (e.g., the Linux process environment,
                the operating Kubernetes Pod).
        Example:
            >>> settings.environment_variables
            [
                'PAT',
                'SECRET_KEY',
                'FERNET_ENCRYPTION_KEY',
                'ENVIRONMENT',
                'PYTHONPATH',
                'DEVELOPER_MODE',
                'GEMINI_API_KEY',
                'ANTHROPIC_API_KEY',
                'COHERE_API_KEY',
                'FIREWORKS_API_KEY',
                'LLAMA_API_KEY',
                'MISTRAL_API_KEY',
                'OPENAI_API_KEY',
                'TOGETHERAI_API_KEY',
                'GOOGLE_SERVICE_ACCOUNT_B64',
                'GOOGLE_MAPS_API_KEY',
                'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY',
                'SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET',
                'SOCIAL_AUTH_GITHUB_KEY',
                'SOCIAL_AUTH_GITHUB_SECRET',
                'SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY',
                'SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET',
                'MAILCHIMP_API_KEY',
                'MAILCHIMP_LIST_ID',
                'PINECONE_API_KEY',
                'PINECONE_ENVIRONMENT',
                'ROOT_DOMAIN',
                'NAMESPACE',
                'MYSQL_HOST',
                'MYSQL_PORT',
                'MYSQL_DATABASE',
                'MYSQL_PASSWORD',
                'MYSQL_USERNAME',
                'MYSQL_ROOT_USERNAME',
                'MYSQL_ROOT_PASSWORD',
                'LOGIN_URL',
                'ADMIN_PASSWORD',
                'ADMIN_USERNAME',
                'DOCKER_IMAGE'
            ]

        Note:
            This list reflects the environment at the time the settings object was created.
        """
        return list(os.environ.keys())

    @property
    def smarter_api_key_max_lifetime_days(self) -> int:
        """Maximum lifetime for Smarter API keys in days.

        Returns:
            int: The number of days.

        Example:
            >>> print(smarter_settings.smarter_api_key_max_lifetime_days)
            90

        Warning:
            Changing this value requires a platform rebuild/redeploy.
            Expired API keys still function but will log warnings.

        See Also:
            - SMARTER_API_KEY_MAX_LIFETIME_DAYS
        """
        return SMARTER_API_KEY_MAX_LIFETIME_DAYS

    @cached_property
    def version(self) -> str:
        """
        Current version of the Smarter platform codebase based on the semantic version currently persisted to smarter.__version__.py.

        Example:
            >>> print(smarter_settings.version)
            '0.13.35'

        Note:
            This value is managed by the NPM semantic-release tooling
            process and should not be modified manually. Versions are
            bumped automatically via a GitHub Actions workflow that is
            executed on merges to the main branch. The nature of the
            version bump is based on commit messages in the merge.
            See https://github.com/smarter-sh/smarter/blob/main/docs/legacy/SEMANTIC_VERSIONING.md for more information.
        """
        return get_semantic_version()

    @cached_property
    def repository_url(self) -> str:
        """
        The https url of the source code repository of the running platform, without credentials.

        Taken from ``git remote -v`` (the ``origin`` remote's fetch url), so that a fork links
        to its own repository, and its own GitHub Actions badges. The Docker image has no
        ``.git`` directory, so a platform running in a container gets the default,
        :data:`~smarter.common.const.SMARTER_PROJECT_REPOSITORY_URL`. See
        :func:`smarter.common.utils.repository.get_repository_url`.

        Example:
            >>> print(smarter_settings.repository_url)
            'https://github.com/smarter-sh/smarter'
        """
        return get_repository_url()

    @cached_property
    def python_version(self) -> str:
        """
        Current version of Python running the Smarter platform codebase.

        Example:
            >>> print(smarter_settings.python_version)
            '3.10.12'
        """
        try:
            # pylint: disable=import-outside-toplevel
            import platform as sys_platform

            return sys_platform.python_version()
        # pylint: disable=broad-except
        except Exception:  # catch broad exceptions to avoid any issues with retrieving Python version
            return "Unknown Python version"

    @cached_property
    def pydantic_version(self) -> str:
        """
        Current version of Pydantic running the Smarter platform codebase.

        Example:
            >>> print(smarter_settings.pydantic_version)
            '2.10.4'
        """
        try:
            # pylint: disable=import-outside-toplevel
            import pydantic

            return pydantic.__version__
        # pylint: disable=broad-except
        except Exception:  # catch broad exceptions to avoid any issues with retrieving Pydantic version
            return "Unknown Pydantic version"

    @cached_property
    def drf_version(self) -> str:
        """
        Current version of Django REST Framework running the Smarter platform codebase.

        Example:
            >>> print(smarter_settings.drf_version)
            '3.14.0'
        """
        try:
            # pylint: disable=import-outside-toplevel
            import rest_framework

            return rest_framework.VERSION
        # pylint: disable=broad-except
        except Exception:  # catch broad exceptions to avoid any issues with retrieving DRF version
            return "Unknown DRF version"

    @cached_property
    def linux_distribution(self) -> str:
        """
        Current Linux distribution running the Smarter platform codebase.

        Example:
            >>> print(smarter_settings.linux_distribution)
            'Ubuntu 20.04.6 LTS (Focal Fossa)'

        Note:
            This is based on the platform module's linux_distribution function, which is deprecated in Python 3.8 and removed in Python 3.10.
            As a result, this method uses a fallback approach to attempt to retrieve Linux distribution information from common files like /etc/os-release.
            If the platform module's linux_distribution function is available, it will be used; otherwise, the fallback approach will be attempted.
            Due to the deprecation and removal of linux_distribution, the returned value may be "Unknown Linux distribution" in some environments or Python versions.
        """
        try:
            # pylint: disable=import-outside-toplevel
            import platform

            if hasattr(platform, "platform"):
                return " ".join(
                    platform.platform().split("-")[:2]
                )  # Get the first two components of the platform string
            else:
                return "Unknown Linux distribution"
        # pylint: disable=broad-except
        except Exception:
            return "Unknown Linux distribution"

    @cached_property
    def django_version(self) -> str:
        """
        Current version of Django installed in the Smarter platform codebase.

        Example:
            >>> print(smarter_settings.django_version)
            '4.2.7'
        """
        try:
            # pylint: disable=import-outside-toplevel
            import django

            return django.get_version()
        # pylint: disable=broad-except
        except ImportError:
            return "Django not installed"
        except Exception:  # catch broad exceptions to avoid any issues with retrieving Django version
            return "Unknown Django version"

    @property
    def cache_path(self) -> str:
        """
        Return the path to the cache directory.

        Example:
            >>> print(smarter_settings.cache_path)
            '/home/smarter_user/.cache'

        Note:
            This is based on the Dockerfile located in the root of the repository.
            Settings are `chmod -R 700 /home/smarter_user/.cache`
            See ./Dockerfile for more information.
        """
        return "/home/smarter_user/.cache"


__all__ = ["ProjectSettings"]
