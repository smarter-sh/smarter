"""
Pydantic models of the plugin data that the REST api's responses include.

:class:`PluginApiPluginMeta` is a plugin's metadata, as the REST api returns it, e.g. in an
LLMClient's plugins. It is the output of :class:`smarter.apps.plugin.serializers.PluginMetaSerializer`,
which the REST api returned before it was modeled, and which clients already read: the owner is
nested, rather than its id.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete

if TYPE_CHECKING:
    from smarter.apps.plugin.models import PluginMeta


PluginApiPluginClass = Literal["api", "skill", "sql", "static", "websearch", "imagesearch"]
"""A plugin's class: the choices of ``PluginMeta.plugin_class``.

A test fails if the two differ.
"""


class PluginApiPluginMeta(AccountApiModel):
    """A plugin's metadata: a :class:`smarter.apps.plugin.models.PluginMeta`."""

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    user_profile: AccountApiUserProfile = Field(..., description="The plugin's owner.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    plugin_class: PluginApiPluginClass = Field(..., description="PluginMeta.plugin_class.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    manifest_url: str = Field(..., description="The url of the plugin's manifest in the web console.")
    ready: bool = Field(..., description="Whether the plugin has the data and configuration that it needs.")
    kind: str = Field(..., description="The plugin's SAM kind, e.g. SqlPlugin.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the plugin now: they own it, and nothing depends on it.",
    )

    @classmethod
    def from_model(cls, plugin_meta: "PluginMeta", user: object = None) -> "PluginApiPluginMeta":
        """
        The contract's model of a plugin's metadata.

        :param plugin_meta: The row, whose ``user_profile`` and tags should be fetched with it.
        :type plugin_meta: smarter.apps.plugin.models.PluginMeta
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: PluginApiPluginMeta
        """
        kind = plugin_meta.kind.value
        return cls(
            id=plugin_meta.pk,
            created_at=plugin_meta.created_at,
            updated_at=plugin_meta.updated_at,
            name=plugin_meta.name,
            user_profile=AccountApiUserProfile.from_model(plugin_meta.user_profile),
            description=plugin_meta.description,
            plugin_class=plugin_meta.plugin_class,  # type: ignore[arg-type]
            version=plugin_meta.version,
            annotations=plugin_meta.annotations,
            tags=[tag.name for tag in plugin_meta.tags.all()],
            manifest_url=plugin_meta.manifest_url,
            ready=plugin_meta.ready,
            kind=kind,
            can_delete=user_can_delete(plugin_meta, kind, user),
        )


__all__ = ["PluginApiPluginClass", "PluginApiPluginMeta"]
