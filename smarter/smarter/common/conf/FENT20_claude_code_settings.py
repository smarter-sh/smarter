# Created with the assistance of Claude (Anthropic), using our team's original
# ideas to meet the requirements of the capstone project for the AI Integration
# in Enterprise course.
"""Generate Claude Code settings from a Smarter ``Provider`` manifest.

The Smarter ``Provider`` manifest applied in the "Getting Started: Claude Code
with Smarter" tutorial records which Anthropic model Smarter is registered to
use. This module reads that manifest and produces the matching Claude Code
``settings.json``, so the model is defined in one place.

Example::

    manifest = load_provider_manifest("anthropic-sonnet.yaml")
    settings = ClaudeCodeSettings(
        manifest,
        gateway_url="https://smarter.napl.example/claude",
    )
    write_settings(settings, "~/.claude/settings.json")
"""

import json
import os
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlparse

import yaml

SUPPORTED_API_VERSION = "smarter.sh/v1"
"""The Smarter manifest ``apiVersion`` this module understands."""

ANTHROPIC_PROVIDER_NAME = "anthropic"
"""The ``spec.provider.name`` value that identifies an Anthropic provider."""

_LOCAL_HOSTS = ("localhost", "127.0.0.1")


class ClaudeCodeSettings:
    """Claude Code settings derived from a Smarter ``Provider`` manifest.

    The model comes from the manifest. The gateway URL and API key are not in
    the manifest, so the caller supplies them. The API key is never included
    in ``env``, in ``repr()``, or in generated settings unless ``settings()``
    is called with ``include_token=True``.

    Args:
        manifest (dict[str, Any]): A parsed Smarter ``Provider`` manifest.
        gateway_url (str): Address of the Claude Code gateway endpoint
            published by the platform team.
        api_key (Optional[str]): Optional personal Smarter API key.

    Raises:
        ValueError: If the manifest is not a valid Anthropic ``Provider``
            manifest, or if ``gateway_url`` is not acceptable.

    """

    def __init__(
        self,
        manifest: dict[str, Any],
        gateway_url: str,
        api_key: Optional[str] = None,
    ) -> None:
        self._model: str = self._extract_model(manifest)
        self._gateway_url: str = ""
        self.gateway_url = gateway_url
        self._api_key: Optional[str] = api_key

    def __repr__(self) -> str:
        return (
            f"ClaudeCodeSettings(model={self._model!r}, "
            f"gateway_url={self._gateway_url!r})"
        )

    @property
    def gateway_url(self) -> str:
        """The gateway address that Claude Code will send requests to.

        Assigning a new value validates it and removes any trailing slash.

        Returns:
            str: The validated gateway URL, without a trailing slash.

        Raises:
            ValueError: On assignment, if the value is not an ``https`` URL.
                Plain ``http`` is accepted only for ``localhost`` and
                ``127.0.0.1``.

        """
        return self._gateway_url

    @gateway_url.setter
    def gateway_url(self, value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"gateway_url must be an http(s) URL, got {value!r}")
        if parsed.scheme == "http" and parsed.hostname not in _LOCAL_HOSTS:
            raise ValueError("plain http is only allowed for localhost")
        self._gateway_url = value.rstrip("/")

    @property
    def model(self) -> str:
        """The Anthropic model ID taken from ``spec.provider.model``.

        Returns:
            str: The model identifier, for example ``claude-sonnet-5-5``.

        """
        return self._model

    @property
    def env(self) -> dict[str, str]:
        """The non-secret environment variables Claude Code needs.

        Safe to print or log, because it never contains the API key.

        Returns:
            dict[str, str]: A new dictionary with ``ANTHROPIC_BASE_URL`` and
            ``ANTHROPIC_MODEL``.

        """
        return {
            "ANTHROPIC_BASE_URL": self._gateway_url,
            "ANTHROPIC_MODEL": self._model,
        }

    def settings(self, include_token: bool = False) -> dict[str, Any]:
        """Build the contents of a Claude Code ``settings.json`` file.

        Args:
            include_token (bool): If ``True``, add ``ANTHROPIC_AUTH_TOKEN``.
                Leave ``False`` to keep the key out of the file and export it
                in your shell instead.

        Returns:
            dict[str, Any]: A dictionary of the form ``{"env": {...}}``.

        Raises:
            ValueError: If ``include_token`` is ``True`` but no API key was
                supplied.

        """
        env = self.env
        if include_token:
            if not self._api_key:
                raise ValueError("include_token=True requires an api_key")
            env["ANTHROPIC_AUTH_TOKEN"] = self._api_key
        return {"env": env}

    @staticmethod
    def _extract_model(manifest: dict[str, Any]) -> str:
        """Validate a ``Provider`` manifest and return its model ID.

        Args:
            manifest (dict[str, Any]): A parsed manifest.

        Returns:
            str: The value of ``spec.provider.model``.

        Raises:
            ValueError: If any required part is missing or wrong.

        """
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be a mapping")
        if manifest.get("apiVersion") != SUPPORTED_API_VERSION:
            raise ValueError(
                f"unsupported apiVersion {manifest.get('apiVersion')!r}, "
                f"expected {SUPPORTED_API_VERSION!r}"
            )
        if manifest.get("kind") != "Provider":
            raise ValueError(f"expected kind 'Provider', got {manifest.get('kind')!r}")
        provider = (manifest.get("spec") or {}).get("provider") or {}
        if provider.get("name") != ANTHROPIC_PROVIDER_NAME:
            raise ValueError(
                f"spec.provider.name must be {ANTHROPIC_PROVIDER_NAME!r}, "
                f"got {provider.get('name')!r}"
            )
        model = provider.get("model")
        if not isinstance(model, str) or not model:
            raise ValueError("spec.provider.model is missing")
        return model


def load_provider_manifest(path: Union[str, Path]) -> dict[str, Any]:
    """Read a Smarter manifest from a YAML file.

    Args:
        path (Union[str, Path]): Location of the YAML file, for example
            ``anthropic-sonnet.yaml``.

    Returns:
        dict[str, Any]: The parsed manifest.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file does not contain a YAML mapping.

    """
    with open(Path(path).expanduser(), encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a YAML mapping")
    return data


def write_settings(
    settings: ClaudeCodeSettings,
    path: Union[str, Path],
    include_token: bool = False,
) -> Path:
    """Write Claude Code settings to a JSON file readable only by you.

    Args:
        settings (ClaudeCodeSettings): The settings to write.
        path (Union[str, Path]): Destination, for example
            ``~/.claude/settings.json``.
        include_token (bool): Passed to ``ClaudeCodeSettings.settings()``.

    Returns:
        Path: The path that was written.

    Raises:
        ValueError: If ``include_token`` is ``True`` but the settings have no
            API key.

    """
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings.settings(include_token), indent=2) + "\n"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
    os.chmod(target, 0o600)
    return target
