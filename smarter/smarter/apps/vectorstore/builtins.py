"""
The built-in Vectorstores: example vector databases, which every account may use.

``manage.py add_builtin_vectorstores``, which ``manage.py initialize_platform`` calls, applies the
Vectorstore manifests in ``smarter/apps/vectorstore/data/vectorstores`` for the Smarter admin. They
are applied, but not deployed, so that no database is created, nor paid for, until someone
deploys one. A manifest is skipped if its embeddings Provider, or its ApiConnection, does not
exist, e.g. because ``PINECONE_API_KEY`` is not set.
"""

import glob
import os
from dataclasses import dataclass, field
from typing import Optional

from django.test import RequestFactory

from smarter.apps.account.models import UserProfile
from smarter.apps.connection.models import ApiConnection
from smarter.apps.provider.models import Provider
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.loader import SAMLoader

from .const import BUILTIN_VECTORSTORE_PATH
from .models import VectorstoreMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])
logger_prefix = logging.formatted_text(__name__)


@dataclass
class BuiltinVectorstoresResult:
    """The outcome of :func:`add_builtin_vectorstores`: the names of the Vectorstores, by outcome."""

    applied: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    failed: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.failed


def builtin_manifest_files(path: str = BUILTIN_VECTORSTORE_PATH) -> list[str]:
    """The built-in Vectorstore manifests' files, in name order."""
    return sorted(glob.glob(os.path.join(path, "*.yaml")))


def missing_dependency(loader: SAMLoader, user_profile: UserProfile) -> Optional[str]:
    """Why a manifest cannot be applied for a user: its Provider or ApiConnection does not exist.

    Else None.
    """
    spec = loader.manifest_spec or {}
    provider = (spec.get("embeddings") or {}).get("provider")
    if not Provider.objects.filter(name=provider).with_read_permission_for(user_profile.user).exists():  # type: ignore[attr-defined]
        return f"Provider {provider} does not exist"
    connection = spec.get("connection")
    if connection and not ApiConnection.objects.filter(name=connection).with_read_permission_for(user_profile.user).exists():  # type: ignore[attr-defined]
        return f"ApiConnection {connection} does not exist"
    return None


def add_builtin_vectorstores(
    user_profile: Optional[UserProfile] = None, path: str = BUILTIN_VECTORSTORE_PATH
) -> BuiltinVectorstoresResult:
    """
    Apply the built-in Vectorstore manifests for a user.

    They are not deployed.

    A Vectorstore that already exists is applied again, which updates it, unless it is deployed
    and its index would change. One that fails is logged, and the others are still applied.

    :param user_profile: The owner. Defaults to the Smarter admin.
    """
    # pylint: disable=C0415
    from smarter.apps.account.utils import smarter_cached_objects
    from smarter.apps.vectorstore.manifest.brokers.vectorstore import (
        SAMVectorstoreBroker,
    )

    user_profile = user_profile or smarter_cached_objects.smarter_admin_user_profile
    result = BuiltinVectorstoresResult()
    for filename in builtin_manifest_files(path):
        name = os.path.splitext(os.path.basename(filename))[0]
        try:
            loader = SAMLoader(file_path=filename)
            name = (loader.manifest_metadata or {}).get("name", name)
            reason = missing_dependency(loader, user_profile)
            if reason:
                logger.warning("%s skipped built-in Vectorstore %s: %s.", logger_prefix, name, reason)
                result.skipped[name] = reason
                continue
            request = RequestFactory().post("/", data=loader.manifest, content_type="application/json")
            request.user = user_profile.user
            broker = SAMVectorstoreBroker(request=request, loader=loader, user_profile=user_profile)
            broker.apply(request=request)
            result.applied.append(name)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("%s failed to apply built-in Vectorstore %s from %s: %s", logger_prefix, name, filename, e)
            result.failed.append(name)
    return result


def builtin_vectorstores():
    """The built-in Vectorstores: those that the Smarter admin owns, which every account may use."""
    # pylint: disable=C0415
    from smarter.apps.account.utils import smarter_cached_objects

    return VectorstoreMeta.objects.filter(user_profile=smarter_cached_objects.smarter_admin_user_profile)


__all__ = [
    "BuiltinVectorstoresResult",
    "add_builtin_vectorstores",
    "builtin_manifest_files",
    "builtin_vectorstores",
]
