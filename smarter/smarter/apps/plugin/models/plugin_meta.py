# pylint: disable=W0613
"""PluginMeta model for defining the selection strategy and search terms for Smarter plugins."""

from typing import Optional

from django.db import models
from django.db.models import QuerySet

from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
    User,
    UserProfile,
)
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClassValues,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import rfc1034_compliant_str, to_snake_case
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


class PluginMeta(MetaDataWithOwnershipModel, SmarterHelperMixin):
    """
    Represents the core metadata for a Smarter plugin, serving as the central registry for all plugin types.

    This class defines the essential identifying and descriptive information for a plugin, including its name,
    description, type (static, SQL, or API), version, user_profile, and associated tags. Each plugin is uniquely
    associated with an account and a user_profile, ensuring that plugin names are unique per account and
    enforcing a snake_case naming convention for consistency and compatibility.

    The ``PluginMeta`` model acts as the anchor point for related plugin configuration and data models, such as
    :class:`PluginDataStatic`, :class:`PluginDataSql`, and :class:`PluginDataApi`, which store the specific
    data and behavior for each plugin type. It is also linked to selection and prompt configuration through
    :class:`PluginSelector` and :class:`PluginPrompt`, enabling flexible plugin discovery and LLM prompt customization.

    Validation logic within this class ensures that plugin names conform to required standards, and class methods
    provide efficient, cached access to plugin instances for a given user or account.

    This model is foundational for the Smarter plugin system, enabling the organization, discovery, and management
    of all plugins within an account, and supporting integration with the broader plugin data and connection models
    defined in this module.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        verbose_name = "Plugin"
        verbose_name_plural = "Plugins"
        unique_together = ("user_profile", "name")

    objects: MetaDataWithOwnershipModelManager["PluginMeta"] = MetaDataWithOwnershipModelManager()

    PLUGIN_CLASSES = [
        (SAMPluginCommonMetadataClassValues.STATIC.value, SAMPluginCommonMetadataClassValues.STATIC.value),
        (SAMPluginCommonMetadataClassValues.SQL.value, SAMPluginCommonMetadataClassValues.SQL.value),
        (SAMPluginCommonMetadataClassValues.API.value, SAMPluginCommonMetadataClassValues.API.value),
    ]
    """The classes of plugins supported by Smarter."""

    plugin_class = models.CharField(
        choices=PLUGIN_CLASSES, help_text="The class name of the plugin", max_length=255, default="PluginMeta"
    )

    def __str__(self):
        return str(self.user_profile) + " " + str(self.name) or ""

    def save(self, *args, **kwargs):
        """
        Override the save method to validate the field dicts.

        This method ensures that all relevant fields are validated before saving the model instance.
        For example, it checks that the name is in snake_case and converts it if necessary, logs a warning if conversion occurs,
        and calls the model's ``validate()`` method to enforce any additional validation logic defined on the model.
        After validation, it proceeds with the standard Django save operation.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        :return: None
        """
        if isinstance(self.name, str) and not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = to_snake_case(self.name)
            logger.warning(
                "%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                self.formatted_class_name,
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        self.validate()
        super().save(*args, **kwargs)
        if not isinstance(self.name, str) or not self.name:
            raise SmarterValueError("PluginMeta.save(): name is required after save.")

    @property
    def kind(self) -> SAMKinds:
        """
        Return the kind of the plugin based on its class.

        This property is used to determine how the plugin should be handled by the system.
        It maps the plugin's class to a corresponding :class:`SAMKinds` enumeration value.

        :return: The kind of the plugin as a :class:`SAMKinds` enum.
        :rtype: SAMKinds

        **Example:**

        .. code-block:: python

            plugin.plugin_class = 'static'
            plugin.kind  # SAMKinds.STATIC_PLUGIN
        """
        if self.plugin_class == SAMPluginCommonMetadataClassValues.STATIC.value:
            return SAMKinds.STATIC_PLUGIN
        elif self.plugin_class == SAMPluginCommonMetadataClassValues.SQL.value:
            return SAMKinds.SQL_PLUGIN
        elif self.plugin_class == SAMPluginCommonMetadataClassValues.API.value:
            return SAMKinds.API_PLUGIN
        else:
            raise SmarterValueError(f"Unsupported plugin class: {self.plugin_class}")

    @property
    def rfc1034_compliant_kind(self) -> Optional[str]:
        """
        Returns a URL-friendly kind for the llm_client.

        This is a convenience property that returns an RFC 1034-compliant kind for the llm_client,
        suitable for use in URLs and DNS labels.

        **Example:**

        .. code-block:: python

            self.kind  # 'Static'
            self.rfc1034_compliant_kind  # 'static'

        :return: The RFC 1034-compliant kind, or None if ``self.kind`` is not set.
        :rtype: Optional[str]
        """
        if self.kind:
            return rfc1034_compliant_str(self.kind.value)
        return None

    @property
    def manifest_url(self) -> str:
        """
        Returns the URL to the plugin's manifest.

        This property constructs the URL to the plugin's manifest based on its kind and RFC 1034-compliant name.
        The URL follows the pattern: ``/plugins/{kind}/{name}/manifest/``, where ``{kind}`` is the RFC 1034-compliant kind
        of the plugin, and ``{name}`` is the RFC 1034-compliant name of the plugin.

        **Example:**

        .. code-block:: python

            self.rfc1034_compliant_kind  # 'static'
            self.rfc1034_compliant_name  # 'example-plugin
            self.manifest_url  # '/plugins/static/example-plugin/manifest/'
        """
        # pylint: disable=C0415
        from smarter.apps.plugin.urls import PluginReverseNames

        return reverse(
            f"{PluginReverseNames.namespace}:{PluginReverseNames.detailview}",
            kwargs={"name": self.rfc1034_compliant_name},
        )

    @property
    def ready(self) -> bool:
        """
        Returns True if the plugin is ready to be used.

        This property checks if the plugin has all the necessary data and configuration to be considered ready for use.
        The specific criteria for readiness may depend on the plugin class and other factors, and can be implemented as needed.

        :return: True if the plugin is ready, False otherwise.
        :rtype: bool
        """
        return super().ready  # type: ignore[return-value]

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        user: Optional[User] = None,
        user_profile: Optional[UserProfile] = None,
        username: Optional[str] = None,
        account: Optional[Account] = None,
        plugin_class: Optional[str] = None,
        **kwargs,
    ) -> Optional["PluginMeta"]:
        """
        Return a single instance of PluginMeta by primary key or by name and user.

        This method caches the results to improve performance.

        :param name: The name of the plugin to retrieve.
        :type name: str
        :param user: The user who owns the plugin.
        :type user: User
        :param account: The account associated with the plugin.
        :type account: Account
        :param username: The username of the user who owns the plugin.
        :type username: str
        :param invalidate: If True, invalidate the cache for this query.
        :type invalidate: bool
        :return: A PluginMeta instance if found, otherwise None.
        :rtype: Optional[PluginMeta]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginMeta.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, name: %s, user: %s, user_profile: %s, account: %s, plugin_class: %s",
            logger_prefix,
            pk,
            name,
            user.username if user else None,
            user_profile.id if user_profile else None,  # type: ignore[attr-defined]
            account.id if account else None,  # type: ignore[attr-defined]
            plugin_class,
        )

        @cache_results(cls.cache_expiration)
        def _get_model_by_name_and_userprofile_and_plugin_class(
            name: str, user_profile_id: int, plugin_class: str
        ) -> Optional["PluginMeta"]:
            try:
                logger.debug(
                    "%s._get_model_by_name_and_userprofile_and_plugin_class() cache miss for name: %s, user_profile_id: %s, plugin_class: %s",
                    logger_prefix,
                    name,
                    user_profile_id,
                    plugin_class,
                )
                retval = (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(name=name, user_profile_id=user_profile_id, plugin_class=plugin_class)
                )
                logger.debug(
                    "%s._get_model_by_name_and_userprofile_and_plugin_class() fetched and cached PluginMeta for name: %s, user_profile_id: %s, plugin_class: %s",
                    logger_prefix,
                    name,
                    user_profile_id,
                    plugin_class,
                )
                return retval
            except cls.DoesNotExist as e:
                logger.debug(
                    "%s._get_model_by_name_and_userprofile_and_plugin_class() no PluginMeta found for name: %s, user_profile_id: %s, plugin_class: %s",
                    logger_prefix,
                    name,
                    user_profile_id,
                    plugin_class,
                )
                raise cls.DoesNotExist(
                    f"No PluginMeta found for name: {name}, user_profile_id: {user_profile_id}, plugin_class: {plugin_class}"
                ) from e

        if username and not user:
            try:
                user_profile = UserProfile.get_cached_object(invalidate=invalidate, username=username, account=account)  # type: ignore[arg-type]
            except UserProfile.DoesNotExist:
                logger.debug(
                    "%s.get_cached_object() - No UserProfile found for username: %s, account: %s",
                    logger_prefix,
                    username,
                    account.id if account else None,  # type: ignore[attr-defined]
                )
                user_profile = None
            user = user_profile.user if user_profile else None
            account = account or (user_profile.account if user_profile else None)

        try:
            user_profile = user_profile or UserProfile.get_cached_object(invalidate=invalidate, user=user, account=account)  # type: ignore[arg-type]
        except UserProfile.DoesNotExist:
            logger.debug(
                "%s.get_cached_object() - No UserProfile found for user: %s, account: %s",
                logger_prefix,
                user.username if user else None,
                account.id if account else None,  # type: ignore[attr-defined]
            )
            user_profile = None
        if not user_profile and not pk:
            raise SmarterValueError("either a pk or UserProfile + name is required to get a PluginMeta object.")

        if invalidate and user_profile and name:
            _get_model_by_name_and_userprofile_and_plugin_class.invalidate(name, user_profile.id, plugin_class)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if not plugin_class:
            retval = super().get_cached_object(
                *args,
                invalidate=invalidate,
                pk=pk,
                name=name,
                user=user,
                user_profile=user_profile,
                account=account,
                **kwargs,
            )
            if isinstance(retval, PluginMeta):
                return retval
            return None

        if plugin_class:
            return _get_model_by_name_and_userprofile_and_plugin_class(name, user_profile.id, plugin_class)  # type: ignore[return-value]
        retval = super().get_cached_object(*args, invalidate=invalidate, name=name, user_profile=user_profile, **kwargs)
        if isinstance(retval, PluginMeta):
            return retval

    # pylint: disable=W0222
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, user_profile: Optional[UserProfile] = None
    ) -> QuerySet["PluginMeta"]:
        """
        Return a QuerySet of all PluginMeta instances for the given user profile.

        This method caches the results to improve performance.

        :param invalidate: If True, invalidate the cache for this query.
        :type invalidate: bool
        :param user_profile: The user profile whose plugins should be retrieved.
        :type user_profile: UserProfile
        :return: A QuerySet of PluginMeta instances for the user profile.
        :rtype: QuerySet[PluginMeta]
        """

        return super().get_cached_objects(invalidate=invalidate, user_profile=user_profile)  # type: ignore[return-value]

    @classmethod
    def get_cached_plugins_for_user_profile_id(
        cls, invalidate: Optional[bool] = False, user_profile_id: Optional[int] = None
    ) -> list["PluginMeta"]:
        """
        Return a list of all instances of PluginMeta for the given user.

        This method caches the results to improve performance.

        :param user_profile_id: The ID of the user profile whose plugins should be retrieved.
        :type user_profile_id: int
        :param invalidate: Whether to invalidate the cache before retrieving the plugins.
        :type invalidate: bool
        :return: A list of PluginMeta instances for the user profile.
        :rtype: list[PluginMeta]

        See also:

        - :func:`smarter.lib.cache.cache_results`
        """

        try:
            retval = []
            try:
                user_profile = UserProfile.get_cached_object(invalidate=invalidate, pk=user_profile_id)
            except UserProfile.DoesNotExist:
                logger.debug(
                    "%s.get_cached_plugins_for_user_profile_id() - No UserProfile found for id: %s",
                    logger_prefix,
                    user_profile_id,
                )
                user_profile = None
            if not user_profile:
                raise SmarterValueError(f"UserProfile with id {user_profile_id} not found.")
            admin_user = get_cached_admin_user_for_account(invalidate=invalidate, account=user_profile.cached_account)  # type: ignore[arg-type]
            admin_user_profile = UserProfile.get_cached_object(invalidate=invalidate, user=admin_user, account=user_profile.cached_account)  # type: ignore[arg-type]

            def was_already_added(plugin_meta: PluginMeta) -> bool:
                if not plugin_meta:
                    logger.error("%s.dispatch() - plugin_meta is None. This is a bug.", logger_prefix)
                    return False
                for b in retval:
                    if b.id == plugin_meta.id:  # type: ignore[union-attr]
                        return True
                return False

            def get_plugins_for_account() -> QuerySet:
                try:
                    user_plugins = PluginMeta.get_cached_objects(user_profile=user_profile, invalidate=invalidate)
                except PluginMeta.DoesNotExist as e:
                    logger.error(
                        "%s.get_cached_plugins_for_user_profile_id() - Error retrieving user plugins for %s: %s",
                        logger_prefix,
                        user_profile,
                        str(e),
                    )
                    user_plugins = PluginMeta.objects.none()

                try:
                    admin_plugins = PluginMeta.get_cached_objects(user_profile=admin_user_profile, invalidate=invalidate)  # type: ignore[assignment]
                except PluginMeta.DoesNotExist as e:
                    logger.error(
                        "%s.get_cached_plugins_for_user_profile_id() - Error retrieving admin plugins for %s: %s",
                        logger_prefix,
                        admin_user_profile,
                        str(e),
                    )
                    admin_plugins = PluginMeta.objects.none()

                try:
                    smarter_plugins = PluginMeta.get_cached_objects(
                        user_profile=smarter_cached_objects.smarter_admin_user_profile, invalidate=invalidate
                    )
                except PluginMeta.DoesNotExist as e:
                    logger.error(
                        "%s.get_cached_plugins_for_user_profile_id() - Error retrieving smarter plugins for %s: %s",
                        logger_prefix,
                        smarter_cached_objects.smarter_admin_user_profile,
                        str(e),
                    )
                    smarter_plugins = PluginMeta.objects.none()

                @cache_results(15)
                def _combined_plugins_list(use_profile_id: int, class_name: str = PluginMeta.__name__) -> QuerySet:
                    """
                    Short-lived cache for combined plugins list.

                    Combines user, admin, and smarter plugins into a single queryset
                    and caches the result for 15 seconds to improve performance.
                    """

                    combined_plugins = user_plugins | admin_plugins | smarter_plugins
                    combined_plugins = (
                        combined_plugins.distinct()
                        .select_related("user_profile", "user_profile__account", "user_profile__user")
                        .order_by("name")
                    )
                    logger.debug(
                        "%s._combined_plugins_list() fetched and cached combined plugins list for user_profile_id=%s: %d plugins",
                        logger_prefix,
                        use_profile_id,
                        len(combined_plugins),
                    )
                    return combined_plugins

                return _combined_plugins_list(user_profile.id, class_name=PluginMeta.__name__)  # type: ignore[return-value]

            plugins = get_plugins_for_account()

            for plugin_meta in plugins:
                if not was_already_added(plugin_meta):
                    retval.append(plugin_meta)

            return retval

        # pylint: disable=broad-except
        except Exception:
            logger.error(
                "%s.dispatch() - Exception occurred while getting plugins for user_profile %s.",
                logger_prefix,
                user_profile,
            )
            return []
