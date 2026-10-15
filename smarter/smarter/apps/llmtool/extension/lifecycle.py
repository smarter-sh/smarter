"""
An extension's lifecycle: what it creates when it is installed, and removes when it is uninstalled.

Most of an extension's lifecycle is declared, and the platform carries it out:

- **settings** (``[[tool.smarter.settings]]``) are configured in the admin console;
- **waffle switches** (``[[tool.smarter.switches]]``) are created as ``ext_<slug>_<name>``
  on install, and deleted on uninstall;
- **SAM resources**, the manifests in the package's ``manifests/`` directory, are applied
  on install and upgrade, and deleted on uninstall. An upgrade deletes the resources that
  the new version no longer ships.

For anything else, an extension names a subclass of :class:`SmarterExtensionLifecycle` in
``[tool.smarter] lifecycle``, and overrides the hooks it needs:

.. code-block:: python

    from smarter.apps.llmtool.extension import LifecycleContext, SmarterExtensionLifecycle

    class Lifecycle(SmarterExtensionLifecycle):
        def post_install(self, context: LifecycleContext) -> None:
            context.apply_manifest(SECRET_MANIFEST)

        def pre_upgrade(self, context: LifecycleContext) -> None:
            if context.previous_version == "1.0.0":
                ...

Hooks run once per cluster, in the process that carries out the administrator's action,
not in every pod. A ``pre_*`` hook that raises cancels the action, and nothing changes. A
``post_*`` hook that raises leaves the extension installed but disabled, with the error
shown in the admin console.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel

from .protocol import ExtensionLogger, extension_logger

if TYPE_CHECKING:
    from smarter.apps.account.models import UserProfile
    from smarter.apps.llmtool.models import Extension


@dataclass
class LifecycleContext:
    """
    What a lifecycle hook knows, and the helpers it may use.

    :param extension: The extension.
    :param version: The version being installed, upgraded to, enabled, or uninstalled.
    :param previous_version: On an upgrade, the version being replaced; otherwise None.
    :param settings: The extension's settings, as its tools see them.
    :param user_profile: The superuser who is carrying out the action, who owns the resources it creates.
    """

    extension: "Extension"
    version: str
    settings: BaseModel
    user_profile: "UserProfile"
    previous_version: Optional[str] = None
    logger: ExtensionLogger = field(default=None)  # type: ignore[assignment]

    def __post_init__(self):
        if self.logger is None:
            self.logger = extension_logger(self.extension.slug)

    @property
    def slug(self) -> str:
        """The extension's slug."""
        return self.extension.slug

    def apply_manifest(self, manifest: str) -> tuple[str, str]:
        """
        Apply a SAM manifest, owned by :attr:`user_profile`, and record it as created by this extension.

        The resource is deleted when the extension is uninstalled.

        :param manifest: The manifest, as YAML or JSON.
        :returns: The resource's kind and name.
        :raises SmarterExtensionInstallError: If the manifest cannot be applied.
        """
        # pylint: disable=import-outside-toplevel
        from .resources import apply_extension_manifest

        return apply_extension_manifest(self.extension, manifest, self.user_profile, self.version, managed=False)

    def delete_resource(self, kind: str, name: str) -> None:
        """
        Delete a SAM resource that this extension created.

        :param kind: The resource's kind, e.g. ``Secret``.
        :param name: The resource's name.
        """
        # pylint: disable=import-outside-toplevel
        from .resources import delete_extension_resource

        delete_extension_resource(self.extension, kind, name, self.user_profile)


class SmarterExtensionLifecycle:
    """
    The base class of an extension's lifecycle hooks.

    Every hook does nothing unless overridden.

    A new instance is created for each action.
    """

    def pre_install(self, context: LifecycleContext) -> None:
        """Run before an extension is first installed.

        Raise to cancel the install.
        """

    def post_install(self, context: LifecycleContext) -> None:
        """Run after an extension is first installed, its switches created and its manifests applied."""

    def pre_upgrade(self, context: LifecycleContext) -> None:
        """Run, from the new version's code, before it replaces :attr:`LifecycleContext.previous_version`.

        Raise to cancel.
        """

    def post_upgrade(self, context: LifecycleContext) -> None:
        """Run, from the new version's code, after it replaced :attr:`LifecycleContext.previous_version`."""

    def pre_uninstall(self, context: LifecycleContext) -> None:
        """Run before an extension is uninstalled.

        Raise to cancel the uninstall.
        """

    def post_uninstall(self, context: LifecycleContext) -> None:
        """Run after an extension's resources and switches are deleted, just before its rows are."""

    def on_enable(self, context: LifecycleContext) -> None:
        """Run when an administrator enables the extension.

        Raise to keep it disabled.
        """

    def on_disable(self, context: LifecycleContext) -> None:
        """Run when an administrator disables the extension."""


__all__ = ["LifecycleContext", "SmarterExtensionLifecycle"]
