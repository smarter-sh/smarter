"""
The built-in Proxies: one for each of the built-in LLM Providers that has an API key.

``manage.py initialize_providers`` creates the built-in Providers, e.g. openai and anthropic,
and their API key Secrets, from environment variables, e.g. ``OPENAI_API_KEY``.
``manage.py add_builtin_proxies``, which ``manage.py initialize_platform`` calls after it,
applies a Proxy manifest for each of them, from ``smarter/apps/proxy/data/proxy``. The Smarter admin
owns them, so every account may use them.

A manifest is skipped if its Provider, or its API key Secret, does not exist, e.g. because the
environment variable of its API key is not set.
"""

import glob
import os
from dataclasses import dataclass, field
from typing import Optional

from django.test import RequestFactory

from smarter.apps.account.models import UserProfile
from smarter.apps.provider.models import Provider
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.loader import SAMLoader

from .const import BUILTIN_PROXY_PATH
from .models import Proxy

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])
logger_prefix = logging.formatted_text(__name__)


@dataclass
class BuiltinProxiesResult:
    """The outcome of :func:`add_builtin_proxies`: the names of the Proxies, by outcome."""

    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.failed


def builtin_manifest_files(path: str = BUILTIN_PROXY_PATH) -> list[str]:
    """The built-in Proxy manifests' files, in name order."""
    return sorted(glob.glob(os.path.join(path, "*.yaml")))


def missing_dependency(loader: SAMLoader, user_profile: UserProfile) -> Optional[str]:
    """Why a manifest cannot be applied for a user: its Provider or API key Secret does not exist.

    Else ``None``.
    """
    spec = loader.manifest_spec or {}
    provider = spec.get("provider")
    if not Provider.objects.filter(name=provider).with_read_permission_for(user_profile.user).exists():  # type: ignore[attr-defined]
        return f"Provider {provider} does not exist"
    api_key = spec.get("apiKey")
    if api_key and not Secret.objects.filter(name=api_key, user_profile__account=user_profile.account).exists():
        return f"Secret {api_key} does not exist"
    return None


def add_builtin_proxies(
    user_profile: Optional[UserProfile] = None, path: str = BUILTIN_PROXY_PATH
) -> BuiltinProxiesResult:
    """
    Apply the built-in Proxy manifests, in ``data/proxy/``, for a user.

    A manifest whose Provider or Secret does not exist is skipped. One that fails to apply is
    logged, and the others are still applied.

    :param user_profile: The owner. Defaults to the Smarter admin.
    :returns: The names of the Proxies that were applied, skipped, and failed.
    """
    # pylint: disable=C0415
    from smarter.apps.account.utils import smarter_cached_objects
    from smarter.apps.proxy.manifest.brokers.proxy import SAMProxyBroker

    user_profile = user_profile or smarter_cached_objects.smarter_admin_user_profile
    result = BuiltinProxiesResult()
    for filename in builtin_manifest_files(path):
        name = os.path.splitext(os.path.basename(filename))[0]
        try:
            loader = SAMLoader(file_path=filename)
            name = (loader.manifest_metadata or {}).get("name", name)
            reason = missing_dependency(loader, user_profile)
            if reason:
                logger.warning("%s skipped built-in Proxy %s: %s.", logger_prefix, name, reason)
                result.skipped.append(name)
                continue
            request = RequestFactory().post("/", data=loader.manifest, content_type="application/json")
            request.user = user_profile.user
            broker = SAMProxyBroker(request=request, loader=loader, user_profile=user_profile)
            broker.apply(request=request)
            result.applied.append(name)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s failed to apply built-in Proxy %s from %s: %s", logger_prefix, name, filename, e)
            result.failed.append(name)
    return result


def builtin_proxies():
    """The built-in Proxies: those that the Smarter admin owns, which every account may use."""
    # pylint: disable=C0415
    from smarter.apps.account.utils import smarter_cached_objects

    return Proxy.objects.filter(user_profile=smarter_cached_objects.smarter_admin_user_profile)


__all__ = ["BuiltinProxiesResult", "add_builtin_proxies", "builtin_manifest_files", "builtin_proxies"]
