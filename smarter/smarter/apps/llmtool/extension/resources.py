"""
The SAM resources and waffle switches that an extension creates.

Manifests are applied through the real SAM brokers, exactly as ``manage.py apply_manifest``
does, so a resource that an extension creates is the same as one a person applies. Each is
recorded as an :class:`~smarter.apps.llmtool.models.ExtensionResource`, so that uninstalling
the extension deletes exactly what it created.
"""

from typing import TYPE_CHECKING

from django.test import RequestFactory
from waffle import get_waffle_switch_model

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.parsing import parse_manifest

from .exceptions import SmarterExtensionInstallError
from .manifest import ExtensionManifest
from .protocol import switch_name

if TYPE_CHECKING:
    from smarter.apps.account.models import UserProfile
    from smarter.apps.llmtool.models import Extension

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

FAKE_REQUEST_PATH = "/api/v1/cli/apply/"


def apply_extension_manifest(
    extension: "Extension", manifest: str, user_profile: "UserProfile", version: str, managed: bool = True
) -> tuple[str, str]:
    """
    Apply a SAM manifest for an extension, and record the resource it creates.

    :param extension: The extension.
    :param manifest: The manifest, as YAML or JSON.
    :param user_profile: The resource's owner.
    :param version: The extension version that applies it.
    :param managed: Whether it comes from the package's ``manifests/`` directory.
    :returns: The resource's kind and name.
    :raises SmarterExtensionInstallError: If the manifest is not valid, or cannot be applied.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.brokers import Brokers
    from smarter.apps.llmtool.models import ExtensionResource

    try:
        data = parse_manifest(manifest)
    except SAMValidationError as e:
        raise SmarterExtensionInstallError(f"{extension.slug}: a manifest is not valid: {e}") from e
    kind = data.get("kind")
    if not isinstance(kind, str):
        raise SmarterExtensionInstallError(f"{extension.slug}: a manifest is not valid: it has no kind")
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        raise SmarterExtensionInstallError(f"{extension.slug}: a manifest is not valid: it has no metadata")
    name = metadata.get("name")
    if not isinstance(name, str):
        raise SmarterExtensionInstallError(f"{extension.slug}: a manifest is not valid: it has no metadata.name")
    broker_class = Brokers.get_broker(kind)
    if broker_class is None:
        raise SmarterExtensionInstallError(f"{extension.slug}: there is no SAM kind {kind}")
    request = RequestFactory().post(FAKE_REQUEST_PATH, data=data, content_type="application/json")
    request.user = user_profile.user
    try:
        broker = broker_class(request=request, manifest=data, user_profile=user_profile)
        response = broker.apply(request=request)
    # brokers raise many kinds of exceptions, all of which mean the manifest was not applied.
    # pylint: disable=broad-exception-caught
    except Exception as e:
        raise SmarterExtensionInstallError(f"{extension.slug}: could not apply {kind} {name}: {e}") from e
    if response is None or response.status_code != 200:
        status = response.status_code if response is not None else None
        raise SmarterExtensionInstallError(f"{extension.slug}: could not apply {kind} {name} (status {status})")
    ExtensionResource.objects.update_or_create(
        extension=extension,
        kind=kind,
        name=name,
        user_profile=user_profile,
        defaults={"version": version, "managed": managed},
    )
    logger.info("%s applied %s %s", extension.slug, kind, name)
    return kind, name


def delete_extension_resource(extension: "Extension", kind: str, name: str, user_profile: "UserProfile") -> None:
    """
    Delete a resource that an extension created, and forget it.

    A resource that no longer exists is simply forgotten. A failure is logged, and the
    resource is forgotten anyway, so that an uninstall always finishes.

    :param extension: The extension.
    :param kind: The resource's kind.
    :param name: The resource's name.
    :param user_profile: The resource's owner.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.brokers import Brokers
    from smarter.apps.llmtool.models import ExtensionResource

    broker_class = Brokers.get_broker(kind)
    if broker_class is not None:
        request = RequestFactory().post(FAKE_REQUEST_PATH)
        request.user = user_profile.user
        try:
            broker = broker_class(request=request, name=name, kind=kind, user_profile=user_profile)
            broker.delete(request=request)
            logger.info(
                "%s deleted %s %s",
                extension.slug,
                kind,
                name,
            )
        # a broker raises if the resource is already gone, or cannot be deleted.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.warning(
                "%s could not delete %s %s: %s",
                extension.slug,
                kind,
                name,
                e,
            )
    ExtensionResource.objects.filter(extension=extension, kind=kind, name=name, user_profile=user_profile).delete()


def create_switches(manifest: ExtensionManifest) -> list[str]:
    """
    Create an extension's waffle switches, leaving any that already exist as they are.

    :param manifest: The extension's manifest.
    :returns: The names of the switches.
    """
    switch_model = get_waffle_switch_model()
    names = []
    for spec in manifest.smarter.switches:
        name = switch_name(manifest.slug, spec.name)
        switch_model.objects.get_or_create(name=name, defaults={"active": spec.default, "note": spec.description})
        names.append(name)
    return names


def delete_switches(manifest: ExtensionManifest, keep: frozenset[str] = frozenset()) -> None:
    """
    Delete an extension's waffle switches.

    :param manifest: The manifest whose switches are deleted.
    :param keep: Names, without the prefix, of switches not to delete, e.g. those the new version still declares.
    """
    names = [switch_name(manifest.slug, spec.name) for spec in manifest.smarter.switches if spec.name not in keep]
    if names:
        get_waffle_switch_model().objects.filter(name__in=names).delete()


__all__ = ["apply_extension_manifest", "create_switches", "delete_extension_resource", "delete_switches"]
