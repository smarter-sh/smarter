"""Smarter enumeration base helper class."""

import logging
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SmarterEnumAbstract(Enum):
    """Smarter enumeration helper class."""

    @classmethod
    def all(cls) -> list[str]:
        """
        Return a list of all enumeration values.
        """
        retval = [member.value for name, member in cls.__members__.items() if not name.startswith("_")]
        return retval

    @classmethod
    def list_all(cls) -> str:
        """
        Return a comma-separated string of all enumeration values.
        """
        return ", ".join(cls.all())

    @classmethod
    def all_slugs(cls):
        """
        Return a list of all enumeration slugs (singular and plural).
        """
        return cls.singular_slugs() + cls.plural_slugs()

    @classmethod
    def singular_slugs(cls):
        """
        Return a list of singular enumeration slugs.
        """
        return [slug.lower() for slug in cls.all()]

    @classmethod
    def plural_slugs(cls):
        """
        Return a list of plural enumeration slugs.
        """
        return [f"{slug.lower()}s" for slug in cls.all()]

    @classmethod
    def from_url(cls, url) -> Optional[str]:
        """
        Extract the manifest kind from a URL.

        example::

            http://localhost:9357/api/v1/cli/example_manifest/Account/
            http://platform.smarter.sh/api/v1/cli/whoami/
        """
        if isinstance(url, bytes):
            url = url.decode("utf-8")
        parsed_url = urlparse(url)
        path = parsed_url.path
        if isinstance(path, bytes):
            path = path.decode("utf-8")
        slugs = path.split("/")
        if not "api" in slugs:
            return None
        if "whoami" in slugs:
            return None
        if "status" in slugs:
            return None
        if "version" in slugs:
            return None
        for slug in slugs:
            this_slug = str(slug).lower()
            if this_slug in cls.all_slugs():
                return this_slug
        logger.warning("%s.from_url() could not extract manifest kind from URL: %s", cls.__name__, url)
        return None

    def __str__(self) -> str:
        return self.value


class SmarterEnum:
    """Smarter enumeration helper class."""

    @classmethod
    def all(cls) -> list[str]:
        """
        Return a list of all enumeration values.
        """
        return [
            value
            for name, value in cls.__dict__.items()
            if not name.startswith("_") and name.isupper() and isinstance(value, str)
        ]

    @classmethod
    def list_all(cls) -> str:
        """
        Return a comma-separated string of all enumeration values.
        """
        return ", ".join(cls.all())

    def __str__(self) -> str:
        return str(self.value) if hasattr(self, "value") else super().__str__()  # type: ignore
