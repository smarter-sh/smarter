# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.manifest.enum import SAMUserSpecKeys
from smarter.apps.account.models import User
from smarter.apps.account.utils import get_cached_admin_user_for_account
from smarter.apps.plugin.manifest.models.common.plugin.model import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.manifest.models.static_plugin.spec import SAMPluginStaticSpec
from smarter.apps.plugin.models import (
    PluginDataBase,
    PluginDataStatic,
    PluginMeta,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import AbstractBroker, SAMBrokerError
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

logger = logging.getLogger(__name__)

MAX_RESULTS = 1000


class SAMUserBrokerError(SAMBrokerError):
    """Base exception for Smarter API User Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API User Manifest Broker Error"


class SAMTestBroker(AbstractBroker):
    """Test class for unit tests of the abstract broker class."""

    # override the base abstract manifest model with the User model
    # TODO: We shouldn't be using an implementation of the actual
    #           manifest model here. We should be using a test model.
    _manifest: Optional[SAMStaticPlugin] = None
    _pydantic_model: Type[SAMStaticPlugin] = SAMStaticPlugin
    _user: User
    _username: Optional[str] = None
    _orm_instance: Optional[PluginDataBase] = None
    _plugin_meta: Optional[PluginMeta] = None

    @property
    def username(self) -> Optional[str]:
        return self._username

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API User manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.model_dump()  # type: ignore[return-value]
        config_dump = self.camel_to_snake(config_dump)
        return config_dump  # type: ignore[return-value]

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API User manifest dict.
        """
        if not self.user:
            raise SAMUserBrokerError("No user set for the broker")
        user_dict = model_to_dict(self.user) if isinstance(self.user, User) else {}
        user_dict = self.snake_to_camel(user_dict)
        user_dict.pop("id")  # type: ignore[union-attr]

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.user.username,
                SAMMetadataKeys.DESCRIPTION.value: self.user.username,
                SAMMetadataKeys.VERSION.value: "1.0.0",
                "username": self.user.username,
            },
            SAMKeys.SPEC.value: {
                SAMUserSpecKeys.CONFIG.value: user_dict,
            },
            SAMKeys.STATUS.value: {
                "dateJoined": self.user.date_joined.isoformat() if isinstance(self.user, User) else None,
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> Optional[Type[ModelSerializer]]:
        return ModelSerializer

    @property
    def ORMModelClass(self) -> Type[PluginDataStatic]:
        return PluginDataStatic

    @property
    def orm_instance(self) -> Optional[PluginDataBase]:
        """
        Return the Django ORM model instance for the broker.

        :return: The Django ORM model instance for the broker.
        :rtype: Optional[TimestampedModel]
        """
        if self._orm_instance:
            return self._orm_instance

        if not self.ready:
            logger.warning(
                "%s.orm_instance() - broker is not ready. Cannot retrieve ORM instance.",
                self.abstract_broker_logger_prefix,
            )
            return None
        try:
            logger.debug(
                "%s.orm_instance() - attempting to retrieve ORM instance %s for user=%s, name=%s",
                self.abstract_broker_logger_prefix,
                PluginDataBase.__name__,
                self.user,
                self.name,
            )
            instance = PluginDataBase.objects.get(plugin=self.plugin_meta)
            logger.debug(
                "%s.orm_instance() - retrieved ORM instance: %s",
                self.abstract_broker_logger_prefix,
                serializers.serialize("json", [instance]),
            )
            return instance
        except PluginDataBase.DoesNotExist:
            logger.warning(
                "%s.orm_instance() - ORM instance does not exist for account=%s, name=%s",
                self.abstract_broker_logger_prefix,
                self.account,
                self.name,
            )
            return None

    @property
    def plugin_meta(self) -> Optional[PluginMeta]:
        """
        Retrieve the `PluginMeta` ORM instance associated with this broker.

        This property returns the plugin metadata object for the current plugin, resolving it by `name` and `account` if not already cached. If the metadata cannot be found, `None` is returned.

        :return: The `PluginMeta` instance for this broker, or `None` if unavailable.
        :rtype: Optional[PluginMeta]

        .. note::

            The metadata is cached after the first successful lookup for efficient repeated access.

        .. warning::

            If the plugin metadata does not exist in the database, no exception is raised; `None` is returned.

        .. seealso::

            :class:`PluginMeta`
            :meth:`SAMPluginBaseBroker.plugin`
            :meth:`SAMPluginBaseBroker.plugin_data`

        **Example usage**::

            meta = broker.plugin_meta
            if meta:
                print(meta.name, meta.account)
            else:
                print("No plugin metadata found.")

        """
        if self._plugin_meta:
            return self._plugin_meta
        if self.name and self.account:
            try:
                self._plugin_meta = PluginMeta.objects.get(account=self.account, name=self.name)
            except PluginMeta.DoesNotExist:
                logger.warning(
                    "PluginMeta does not exist for name %s and account %s",
                    self.name,
                    self.account,
                )
        return self._plugin_meta

    @plugin_meta.setter
    def plugin_meta(self, value: PluginMeta) -> None:
        self._plugin_meta = value
        self._plugin = None
        self._plugin_meta = None
        self._plugin_prompt = None
        self._plugin_status = None
        if not value:
            return
        self.user_profile = None
        self.account = None
        self.user = None
        self.account = value.account
        self.user = get_cached_admin_user_for_account(value.account)

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMTestBroker()"

    @property
    def kind(self) -> str:
        # TODO: WE SHOULD NOT BE USING AN ACTUAL KIND HERE. WE NEED A
        #           TEST KIND FOR THE TESTS.
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMStaticPlugin]:
        """
        SAMPluginCommon() is a Pydantic model
        that is used to represent the Smarter API User manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMStaticPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMPluginStaticSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().chat(request=request, kwargs=kwargs)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().describe(request=request, kwargs=kwargs)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().delete(request=request, kwargs=kwargs)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().deploy(request=request, kwargs=kwargs)

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().example_manifest(request=request, kwargs=kwargs)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().get(request=request, kwargs=kwargs)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().logs(request=request, kwargs=kwargs)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        return super().undeploy(request=request, kwargs=kwargs)
