# pylint: disable=W0718,C0302
"""Smarter API Proxy Manifest handler."""

from typing import Any, Optional, Type

from django.core import serializers
from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.proxy.manifest.models.enum import SAMPluginSpecCommonData
from smarter.apps.proxy.manifest.models.proxy.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.proxy.manifest.models.proxy.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.proxy.manifest.models.proxy.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.proxy.models import Proxy
from smarter.apps.proxy.signals import broker_ready
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import AbstractBroker, SAMBrokerError
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

from . import ProxySerializer, SAMProxyBrokerError

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = formatted_text(__name__ + ".SAMProxyBroker")


class SAMProxyBroker(AbstractBroker):
    """
    Smarter API Proxy Manifest Broker.

    This class is responsible for
    common tasks including CRUD.
    """

    _proxy: Optional[Proxy] = None

    def plugin_init(self) -> None:
        """Initialize the plugin model instance."""
        self._plugin = None
        self._proxy = None
        self._plugin_prompt = None
        self._plugin_status = None
        self._manifest = None

    @property
    def ORMMetaModelClass(self) -> Type[Proxy]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[Proxy]
        """
        return Proxy

    @property
    def formatted_class_name(self) -> str:
        """
        Return the formatted class name for logging purposes.

        :return: The formatted class name.
        :rtype: str
        """
        class_name = f"{__name__}.{SAMProxyBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def orm_instance(self) -> Optional[PluginDataBase]:
        """
        Return the Django ORM model instance for the broker.

        :return: The Django ORM model instance for the broker.
        :rtype: Optional[TimestampedModel]
        """
        if self._orm_instance:
            return self._orm_instance

        if not self.name:
            logger.debug(
                "%s.orm_instance() - no name provided for %s, cannot retrieve ORM instance",
                self.formatted_class_name,
                self.kind,
            )
            return None
        if not self.user_profile:
            logger.debug(
                "%s.orm_instance() - no user_profile provided for %s, cannot retrieve ORM instance",
                self.formatted_class_name,
                self.kind,
            )
            return None

        try:
            # first try to get the PluginDataBase instance for the name & authenticated user_profile
            logger.debug(
                "%s.orm_instance() - attempting to retrieve %s for %s owned by %s",
                self.formatted_class_name,
                PluginDataBase.__name__,
                self.name,
                self.user_profile,
            )
            if self.plugin_meta:
                self._orm_instance = PluginDataBase.objects.get(id=self.plugin_meta.id)  # type: ignore
            if self._orm_instance:
                logger.debug(
                    "%s.orm_instance() - retrieved %s instance: %s for %s owned by %s",
                    self.formatted_class_name,
                    PluginDataBase.__name__,
                    serializers.serialize("json", [self._orm_instance]),  # type: ignore
                    self.name,
                    self.user_profile,
                )
            else:
                logger.debug(
                    "%s.orm_instance() - no %s instance found for %s owned by %s",
                    self.formatted_class_name,
                    PluginDataBase.__name__,
                    self.name,
                    self.user_profile,
                )
            if self._orm_instance:
                self._orm_meta_instance = self._orm_instance.plugin
                logger.debug(
                    "%s.orm_instance() - retrieved meta instance %s",
                    self.formatted_class_name,
                    self._orm_meta_instance,
                )
                self._proxy = self._orm_meta_instance  # type: ignore
                logger.debug(
                    "%s.orm_instance() - set plugin_meta from self._orm_meta_instance %s",
                    self.formatted_class_name,
                    self._proxy,
                )
            else:
                logger.debug(
                    "%s.orm_instance() - no meta instance found for %s",
                    self.formatted_class_name,
                    self.name,
                )

            return self._orm_instance
        except PluginDataBase.DoesNotExist:
            # next try with account admin
            account_admin_user = get_cached_admin_user_for_account(account=self.account)  # type: ignore
            account_admin_user_profile = UserProfile.get_cached_object(user=account_admin_user)  # type: ignore
            try:
                logger.debug(
                    "%s.orm_instance() attempting to retrieve %s for %s owned by %s.",
                    self.formatted_class_name,
                    self.ORMModelClass.__name__,
                    self.name,
                    account_admin_user_profile,
                )
                plugin_meta = Proxy.objects.get(user_profile=account_admin_user_profile, name=self.name)
                self._orm_instance = PluginDataBase.objects.get(plugin=plugin_meta)
                logger.debug(
                    "%s.orm_instance() - retrieved %s for %s owned by %s",
                    self.formatted_class_name,
                    PluginDataBase.__name__,
                    self.name,
                    account_admin_user_profile,
                )
            except (PluginDataBase.DoesNotExist, Proxy.DoesNotExist):
                # finally try with Smarter platform admin user_profile
                smarter_admin_user_profile = smarter_cached_objects.smarter_admin_user_profile
                try:
                    logger.debug(
                        "%s.orm_instance() attempting to retrieve %s for %s owned by %s.",
                        self.formatted_class_name,
                        self.ORMModelClass.__name__,
                        self.name,
                        smarter_admin_user_profile,
                    )
                    plugin_meta = Proxy.objects.get(user_profile=smarter_admin_user_profile, name=self.name)
                    self._orm_instance = PluginDataBase.objects.get(plugin=plugin_meta)
                    logger.debug(
                        "%s.orm_instance() - retrieved %s for %s owned by %s",
                        self.formatted_class_name,
                        PluginDataBase.__name__,
                        self.name,
                        smarter_admin_user_profile,
                    )
                except (PluginDataBase.DoesNotExist, Proxy.DoesNotExist):
                    logger.warning(
                        "%s.orm_instance() - %s does not exist for %s owned by %s",
                        self.formatted_class_name,
                        PluginDataBase.__name__,
                        self.name,
                        self.user_profile,
                    )
                    return None
                # pylint: disable=broad-except
                except Exception as e:
                    logger.error(
                        "%s.orm_instance() - unexpected error retrieving %s for %s owned by %s: %s",
                        self.formatted_class_name,
                        PluginDataBase.__name__,
                        self.name,
                        smarter_admin_user_profile,
                        e,
                    )
                    return None
            # pylint: disable=broad-except
            except Exception as e:
                logger.error(
                    "%s.orm_instance() - unexpected error retrieving %s for %s owned by %s: %s",
                    self.formatted_class_name,
                    PluginDataBase.__name__,
                    self.name,
                    account_admin_user_profile,
                    e,
                )
                return None

        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.orm_instance() - error retrieving %s for %s owned by %s: %s",
                self.formatted_class_name,
                PluginDataBase.__name__,
                self.name,
                self.user_profile,
                e,
                exc_info=True,
            )
            return None

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        This property determines whether the broker has been properly initialized
        and is ready to perform its functions. A broker is considered ready if
        it has a valid manifest loaded, either from raw data, a loader, or
        existing Django ORM models.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        retval = super().ready
        if not retval:
            logger.warning("%s.ready() AbstractBroker is not ready for %s", logger_prefix, self.kind)
            return False
        retval = bool(self.manifest) or bool(self.plugin) or bool(self.orm_meta_instance)
        logger.debug(
            "%s.ready() manifest or orm presence indicates ready=%s for %s",
            logger_prefix,
            retval,
            self.kind,
        )
        if retval:
            broker_ready.send(sender=self.__class__, broker=self)
        return retval

    @property
    def plugin(self) -> Optional[PluginBase]:
        """
        Smarter API Plugin Manifest Broker.

        This abstract base class provides shared functionality for plugin brokers, including common logic for applying manifest data to Django ORM models. Subclasses must implement the `plugin_data` property to specify the concrete plugin data model.

        Responsibilities include:

        - Handling common tasks for plugin brokers, such as updating metadata and synchronizing manifest data.
        - Providing a standardized `apply()` method to copy manifest data to the database, with validation and logging.
        - Mapping manifest model metadata to the correct plugin class via `PluginController`.

        :param plugin: The plugin instance mapped from manifest metadata. May be set by subclasses or via `PluginController`.
        :type plugin: Optional[PluginBase]
        :param plugin_meta: The plugin metadata ORM instance. May be set by subclasses or resolved by name/account.
        :type plugin_meta: Optional[Proxy]
        :param plugin_data: The plugin data ORM instance. Must be implemented by subclasses.
        :type plugin_data: Optional[PluginDataBase]

        .. attention::

            The `PluginController` is used to map manifest metadata to the correct plugin class instance.

        .. error::
            Any error during manifest application, plugin resolution, or database update is logged and may raise an exception.

        .. seealso::

            :class:`AbstractBroker`
            :class:`PluginBase`
            :class:`Proxy`
            :class:`PluginDataBase`
            :class:`PluginController`

        **Example usage**::

            class MyPluginBroker(SAMProxyBroker):
                @property
                def plugin_data(self):
                    return MyPluginData.objects.get(...)

            broker = MyPluginBroker(...)
            broker.apply(request, manifest_data=manifest_dict)
        """
        if self._plugin:
            return self._plugin
        if not self.user:
            raise SAMBrokerError(
                message="No user set for the broker",
                thing=self.thing,
                command=SmarterJournalCliCommands.PROMPT,
            )
        if not self.user_profile:
            raise SAMBrokerError(
                message="No user profile set for the broker",
                thing=self.thing,
                command=SmarterJournalCliCommands.PROMPT,
            )
        if not self._manifest:
            if self.loader:
                self._manifest = self.loader.json_data

        controller = PluginController(
            request=self.smarter_request,
            user_profile=self.user_profile,
            manifest=self._manifest,  # type: ignore
            plugin_meta=self.plugin_meta if not self._manifest else None,
            name=self.name,
        )
        self._plugin = controller.obj
        if isinstance(self._plugin, PluginBase):
            logger.debug(
                "%s.plugin() - resolved plugin=%s, user_profile=%s",
                logger_prefix,
                self._plugin,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.plugin() - could not resolve plugin. manifest=%s, plugin_meta=%s, name=%s, user_profile=%s.",
                logger_prefix,
                self._manifest,
                self.plugin_meta,
                self.name,
                self.user_profile,
            )
        return self._plugin

    @property
    def plugin_meta(self) -> Optional[Proxy]:
        """
        Retrieve the `Proxy` ORM instance associated with this broker.

        This property returns the plugin metadata object for the current plugin, resolving it by `name` and `account` if not already cached. If the metadata cannot be found, `None` is returned.

        :return: The `Proxy` instance for this broker, or `None` if unavailable.
        :rtype: Optional[Proxy]

        .. note::

            The metadata is cached after the first successful lookup for efficient repeated access.

        .. warning::

            If the plugin metadata does not exist in the database, no exception is raised; `None` is returned.

        .. seealso::

            :class:`Proxy`
            :meth:`SAMProxyBroker.plugin`
            :meth:`SAMProxyBroker.plugin_data`

        **Example usage**::

            meta = broker.plugin_meta
            if meta:
                print(meta.name, meta.account)
            else:
                print("No plugin metadata found.")
        """
        if self._proxy:
            return self._proxy
        if self.orm_meta_instance:
            self._proxy = self.orm_meta_instance  # type: ignore
            return self._proxy
        self._proxy = Proxy.objects.filter(name=self.name).with_read_permission_for(self.user).first()  # type: ignore
        if self._proxy:
            logger.debug(
                "%s.plugin_meta() %s found for %s",
                self.formatted_class_name,
                self._proxy.name,
                self._proxy.user_profile,
            )
            return self._proxy

        if self._manifest:
            logger.warning(
                "%s.plugin_meta() - created ORM instance from manifest for name=%s, user_profile=%s. This should be done elsewhere.",
                logger_prefix,
                self.name,
                self.user_profile,
            )
            self._proxy = Proxy(**self.manifest_to_django_orm())
            self._proxy.save()
        return self._proxy

    @plugin_meta.setter
    def plugin_meta(self, value: Proxy) -> None:
        logger.debug(
            "%s.plugin_meta() setter called - setting Proxy to %s",
            logger_prefix,
            value,
        )
        self._proxy = value
        self._plugin = None
        self._proxy = None
        self._plugin_prompt = None
        self._plugin_status = None
        if not value:
            return
        self.user_profile = None
        self.account = None
        self.user = None
        self.account = value.user_profile.account
        self.user = get_cached_admin_user_for_account(account=value.user_profile.account)

    @property
    def plugin_data(self) -> Optional[PluginDataBase]:
        raise NotImplementedError("plugin_data property must be implemented in the subclass of SAMProxyBroker")

    @property
    def SerializerClass(self) -> Type[ProxySerializer]:
        """
        Returns the serializer class for the broker.

        This property provides the serializer class definition used by the broker
        for serializing and deserializing plugin data. It returns the `ProxySerializer`
        class, which is specifically designed to handle static plugin data serialization.

        :return: The serializer class definition for the broker.
        :rtype: Type[ProxySerializer]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            serializer_class = broker.SerializerClass
            print(serializer_class.__name__)
            # Output: "ProxySerializer"

        .. seealso::

            - `ProxySerializer` for static plugin data serialization.
        """
        return ProxySerializer

    # --------------------------------------------------------------------------
    # ORM to Pydantic conversion methods
    # --------------------------------------------------------------------------
    def plugin_status_pydantic(self) -> Optional[SAMPluginCommonStatus]:
        """
        Get the plugin status as a Pydantic model.

        This method retrieves the plugin status from the Django ORM model and converts it into a Pydantic model (`SAMPluginCommonStatus`). It ensures that the status information is properly formatted for use in manifest serialization and API responses.

        :return: The plugin status as a Pydantic model.
        :rtype: SAMPluginCommonStatus

        .. seealso::

            :class:`SAMPluginCommonStatus`
            :meth:`SAMProxyBroker.plugin_meta`
            :meth:`SAMProxyBroker.plugin`

        **Example usage**::

            status = broker.plugin_status_pydantic()
            print(status.active, status.last_updated)
        """
        if self._plugin_status:
            return self._plugin_status
        if not self.plugin_meta:
            return None
        admin = get_cached_admin_user_for_account(account=self.plugin_meta.user_profile.cached_account)
        if not admin:
            raise SAMProxyBrokerError(
                f"No admin user found for account {self.plugin_meta.user_profile.cached_account}",
                thing=self.kind,
                command=SmarterJournalCliCommands("describe"),
            )
        self._plugin_status = SAMPluginCommonStatus(
            accountNumber=self.plugin_meta.user_profile.cached_account.account_number,
            username=admin.username,
            recordLocator=self.plugin_meta.record_locator,
            created=self.plugin_meta.created_at,
            modified=self.plugin_meta.updated_at,
        )
        return self._plugin_status

    def plugin_metadata_orm2pydantic(self) -> SAMPluginCommonMetadata:
        """
        Convert plugin metadata from the Django ORM model format to the Pydantic manifest format.

        This method transforms the plugin metadata, typically retrieved as a dictionary from the Django ORM (`Proxy`), into a Pydantic model (`SAMPluginCommonMetadata`). It ensures the metadata is properly camel-cased and validated for use in manifest serialization and API responses.

        :return: The plugin metadata as a Pydantic model.
        :rtype: SAMPluginCommonMetadata

        :raises SAMProxyBrokerError:
            If the plugin metadata or plugin instance is not found, or if conversion fails.

        .. error::

            Any error during conversion, such as missing metadata or invalid format, is wrapped and raised as :class:`SAMProxyBrokerError`.

        .. seealso::

            :class:`Proxy`
            :class:`SAMPluginCommonMetadata`
            :meth:`SAMProxyBroker.plugin_meta`
            :meth:`SAMProxyBroker.plugin`

        **Example usage**::

            metadata = broker.plugin_metadata_orm2pydantic()
            print(metadata.name, metadata.description)
        """
        logger.debug(
            "%s.plugin_metadata_orm2pydantic() called for kind=%s, name=%s user=%s",
            logger_prefix,
            self.kind,
            self.name,
            self.user_profile,
        )
        command = SmarterJournalCliCommands("describe")
        if not self._proxy:
            raise SAMProxyBrokerError(
                f"Proxy {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if not self.plugin:
            raise SAMProxyBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        try:
            metadata = model_to_dict(self.plugin_meta)  # type: ignore[no-any-return]
            metadata = json.loads(json.dumps(metadata))
            metadata = self.to_camel_case(metadata)
            if not isinstance(metadata, dict):
                raise SAMProxyBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            logger.debug(
                "%s.describe() Proxy %s %s",
                logger_prefix,
                self.kind,
                metadata,
            )
            metadata = SAMPluginCommonMetadata(**metadata)
            return metadata
        except Proxy.DoesNotExist as e:
            raise SAMProxyBrokerError(
                f"{logger_prefix} {self.kind} Proxy does not exist for {self.plugin.name}",
                thing=self.kind,
                command=command,
            ) from e
        except Exception as e:
            raise SAMProxyBrokerError(message=str(e), thing=self.kind, command=command) from e

    def plugin_data_orm2pydantic(self) -> dict[str, Any]:
        """
        Convert plugin data from the Django ORM model format to the Pydantic manifest format.

        This method transforms plugin data, typically retrieved as a dictionary from the Django ORM (`plugin_data`), into a format suitable for Pydantic manifest models. It handles conversion of nested structures, such as parameters, and ensures all fields are properly camel-cased and validated.

        :return: The plugin data as a dictionary formatted for Pydantic manifest models.
        :rtype: dict[str, Any]

        :raises SAMProxyBrokerError:
            If the plugin or plugin data is not found, or if conversion fails.

        .. note::

            - This method automatically converts parameter definitions from a dict-of-dicts to a list of dicts, merging required flags for each property.
            - The conversion process expects the plugin data to follow the expected ORM structure. Unexpected formats may result in errors.

        .. error::

            Any error during conversion, such as missing plugin data or invalid format, is wrapped and raised as :class:`SAMProxyBrokerError`.

        .. seealso::

            :class:`PluginDataBase`
            :meth:`SAMProxyBroker.plugin_data`
            :meth:`SAMProxyBroker.plugin`
            :class:`SAMPluginSpecCommonData`
            :class:`SmarterJournalCliCommands`

        **Example usage**::

            data = broker.plugin_data_orm2pydantic()
            print(data["parameters"])
        """
        logger.debug(
            "%s.plugin_data_orm2pydantic() called for kind=%s, name=%s user=%s",
            logger_prefix,
            self.kind,
            self.name,
            self.user_profile,
        )
        command = SmarterJournalCliCommands("describe")
        if not self.plugin:
            raise SAMProxyBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if not self.plugin_data:
            raise SAMProxyBrokerError(
                f"Plugin data not found for {self.kind} {self.plugin.name}",
                thing=self.kind,
                command=command,
            )
        plugin_data = model_to_dict(self.plugin_data)  # type: ignore[no-any-return]
        plugin_data = self.to_camel_case(plugin_data)
        if not isinstance(plugin_data, dict):
            raise SAMProxyBrokerError(
                f"Model dump failed for {self.kind} {self.plugin.name}",
                thing=self.kind,
                command=command,
            )

        # pylint: disable=W0105
        """
        before transform, ['parameters']['properties'] is a dict of dicts
            {
                'id': 4171,
                'plugin': 4519,
                'description': 'This SQL query retrieves the Django user record for the username provided.\n',
                'parameters': {
                    'type': 'object',
                    'required': ['username'],
                    'properties': {
                        'unit': {'enum': ['Celsius', 'Fahrenheit'], 'type': 'string', 'description': 'The temperature unit to use.'},
                        'username': {'type': 'string', 'description': 'The username to query.'}
                        },
                    'additionalProperties': False
                },
                'plugindatabasePtr': 4171,
                'connection': 955,
                'sqlQuery': "SELECT * FROM auth_user WHERE username = '{username}';\n",
                'testValues': [{'name': 'username', 'value': 'admin'}, {'name': 'unit', 'value': 'Celsius'}],
                'limit': 10
            }

            after transform, ['parameters']['properties'] becomes a list of dicts where each dict has a 'name' key
            and the value is the original dict, e.g., and, the requirements list is re-merged into the properties dicts
            as the 'required' key (true, false) in each dict:

            {
            'id': 4171,
            'plugin': 4519,
            'description': 'This SQL query retrieves the Django user record for the username provided.\n',
            'parameters': [
                {
                    'name': 'unit',
                    'enum': ['Celsius', 'Fahrenheit'],
                    'type': 'string',
                    'required': false
                    'description': 'The temperature unit to use.'
                },
                {
                    'name': 'username',
                    'type': 'string',
                    'required': true
                    'description': 'The username to query.'
                }
            ],
            'plugindatabasePtr': 4171,
            'connection': 955,
            'sqlQuery': "SELECT * FROM auth_user WHERE username = '{username}';\n",
            'testValues': [{'name': 'username', 'value': 'admin'}, {'name': 'unit', 'value': 'Celsius'}],
            'limit': 10
            }
        """
        if SAMPluginSpecCommonData.PARAMETERS.value in plugin_data:
            parameters = plugin_data[SAMPluginSpecCommonData.PARAMETERS.value]
            if (
                isinstance(parameters, dict)
                and "properties" in parameters
                and isinstance(parameters["properties"], dict)
            ):
                properties_dict = parameters["properties"]
                required_list = parameters.get("required", [])
                # Convert dict of dicts to list of dicts with 'name' and 'required' keys
                properties_list = []
                for k, v in properties_dict.items():
                    prop = {"name": k, **v}
                    prop["required"] = k in required_list
                    properties_list.append(prop)
                plugin_data[SAMPluginSpecCommonData.PARAMETERS.value] = properties_list

        return plugin_data

    @property
    def plugin_prompt_orm(self) -> Optional[PluginPrompt]:
        """
        Retrieve the `PluginPrompt` ORM instance associated with this broker.

        This property returns the plugin prompt object for the current plugin metadata. If the prompt cannot be found, `None` is returned.

        :return: The `PluginPrompt` instance for this broker, or `None` if unavailable.
        :rtype: Optional[PluginPrompt]

        .. note::

            The prompt is retrieved based on the associated `Proxy`.
        """
        if self._plugin_prompt:
            return self._plugin_prompt
        if self.plugin_meta is None:
            return None
        try:
            logger.debug(
                "%s.plugin_prompt_orm() called for kind=%s, name=%s user=%s",
                logger_prefix,
                self.kind,
                self.name,
                self.user_profile,
            )
            self._plugin_prompt = PluginPrompt.get_cached_prompt_by_plugin(plugin=self.plugin_meta)
        except PluginPrompt.DoesNotExist:
            logger.warning(
                "PluginPrompt does not exist for Proxy %s",
                self.plugin_meta.name,
            )
            return None
        return self._plugin_prompt

    def plugin_prompt_orm2pydantic(self) -> SAMPluginCommonSpecPrompt:
        """
        Convert plugin prompt data from the Django ORM model format to the Pydantic manifest format.

        This method transforms the plugin prompt data, typically retrieved as a dictionary from the Django ORM (`PluginPrompt`), into a Pydantic model (`SAMPluginCommonSpecPrompt`). It ensures the prompt data is properly camel-cased and validated for use in manifest serialization and API responses.

        :return: The plugin prompt data as a Pydantic model.
        :rtype: SAMPluginCommonSpecPrompt
        :raises SAMProxyBrokerError:
            If the plugin prompt or plugin instance is not found, or if conversion fails.

        .. error::

            Any error during conversion, such as missing prompt data or invalid format, is wrapped and raised as :class:`SAMProxyBrokerError`.

        .. seealso::

            :class:`PluginPrompt`
            :class:`SAMPluginCommonSpecPrompt`
            :meth:`SAMProxyBroker.plugin_prompt`
            :meth:`SAMProxyBroker.plugin`

        **Example usage**::

            prompt = broker.plugin_prompt_orm2pydantic()
            print(prompt.template, prompt.variables)
        """
        logger.debug(
            "%s.plugin_prompt_orm2pydantic() called for kind=%s, name=%s user=%s",
            logger_prefix,
            self.kind,
            self.name,
            self.user_profile,
        )
        command = SmarterJournalCliCommands("describe")
        if self.plugin_meta is None:
            raise SAMProxyBrokerError(
                f"Proxy {self.name} not found",
                thing=self.kind,
                command=command,
            )

        if self.plugin is None:
            raise SAMProxyBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if self.plugin_prompt_orm is None:
            raise SAMProxyBrokerError(
                f"PluginPrompt not found for {self.kind} {self.plugin_meta.name}",
                thing=self.kind,
                command=command,
            )
        plugin_prompt = SAMPluginCommonSpecPrompt(
            provider=self.plugin_prompt_orm.provider,
            systemRole=self.plugin_prompt_orm.system_role,
            model=self.plugin_prompt_orm.model,
            temperature=self.plugin_prompt_orm.temperature,
            maxTokens=self.plugin_prompt_orm.max_completion_tokens,
        )
        return plugin_prompt

    def plugin_selector_orm2pydantic(self) -> SAMPluginCommonSpecSelector:
        """
        Convert plugin selector data from the Django ORM model format to the Pydantic manifest format.

        This method transforms the plugin selector data, typically retrieved as a dictionary from the Django ORM (`PluginSelector`), into a Pydantic model (`SAMPluginCommonSpecSelector`). It ensures the selector data is properly camel-cased and validated for use in manifest serialization and API responses.

        :return: The plugin selector data as a Pydantic model.
        :rtype: SAMPluginCommonSpecSelector

        :raises SAMProxyBrokerError:
            If the plugin selector, plugin metadata, or plugin instance is not found, or if conversion fails.

        .. error::
            Any error during conversion, such as missing selector data or invalid format, is wrapped and raised as :class:`SAMProxyBrokerError`.

        .. seealso::

            :class:`PluginSelector`
            :class:`SAMPluginCommonSpecSelector`
            :meth:`SAMProxyBroker.plugin`
            :meth:`SAMProxyBroker.plugin_meta`

        **Example usage**::

            selector = broker.plugin_selector_orm2pydantic()
            print(selector.type, selector.options)
        """
        command = SmarterJournalCliCommands("describe")
        logger.debug(
            "%s.plugin_selector_orm2pydantic() called for kind=%s, name=%s user=%s",
            logger_prefix,
            self.kind,
            self.name,
            self.user_profile,
        )
        if self.plugin is None:
            raise SAMProxyBrokerError(
                f"Plugin {self.name} not found",
                thing=self.kind,
                command=command,
            )
        if self.plugin_meta is None:
            raise SAMProxyBrokerError(
                f"Proxy {self.name} not found",
                thing=self.kind,
                command=command,
            )
        try:
            plugin_selector = PluginSelector.get_cached_selector_by_plugin(plugin=self.plugin_meta)
            plugin_selector = model_to_dict(plugin_selector)  # type: ignore[no-any-return]
            plugin_selector = self.to_camel_case(plugin_selector)
            if not isinstance(plugin_selector, dict):
                raise SAMProxyBrokerError(
                    f"Model dump failed for {self.kind} {self.plugin.name}",
                    thing=self.kind,
                    command=command,
                )
            logger.debug(
                "%s.describe() PluginSelector %s %s",
                logger_prefix,
                self.kind,
                plugin_selector,
            )
            plugin_selector = SAMPluginCommonSpecSelector(**plugin_selector)
            return plugin_selector
        except PluginSelector.DoesNotExist as e:
            raise SAMProxyBrokerError(
                f"{logger_prefix} {self.kind} PluginSelector does not exist for {self.plugin_meta.name}",
                thing=self.kind,
                command=command,
            ) from e
        except Exception as e:
            raise SAMProxyBrokerError(message=str(e), thing=self.kind, command=command) from e

    def cache_invalidations(self) -> None:
        """Invalidate relevant cache entries for the plugin metadata and data."""
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)
        if self.plugin_meta:
            Proxy.get_cached_object(invalidate=True, pk=self.plugin_meta.id)  # type: ignore
        return super().cache_invalidations()

    def apply(self, request: HttpRequest, *args, **kwargs) -> Optional[SmarterJournaledJsonResponse]:
        """
        Apply the manifest to the Django ORM model and persist changes to the database.

        This method copies the manifest data to the corresponding Django ORM model and saves the model instance. Logging is performed to record the invocation and parameters.

        :param request: The HTTP request initiating the manifest application.
        :type request: HttpRequest
        :param args: Additional positional arguments passed to the method.
        :type args: tuple
        :param kwargs: Additional keyword arguments, typically including manifest data.
        :type kwargs: dict
        :return: Optionally returns a `SmarterJournaledJsonResponse` if the operation produces a journaled response, otherwise `None`.
        :rtype: Optional[SmarterJournaledJsonResponse]

        .. attention::

            - Any error during manifest application, such as validation failure or database error, will be logged and may raise a `SAMProxyBrokerError`.

        .. seealso::

            :meth:`AbstractBroker.apply`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMProxyBrokerError`

        **Example usage**::

            response = broker.apply(request, manifest_data=manifest_dict)
            if response:
                print(response.status, response.data)
        """
        logger.debug("%s.apply() called %s with args: %s, kwargs: %s", logger_prefix, request, args, kwargs)

        if request.user != self.user:
            raise SAMBrokerError(
                message=f"This plugin is owned by {self.user_profile}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )

    def get(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with a list of SQL plugins for this account.

        This method queries the database for all SQL plugins associated with the current account,
        optionally filtered by name, and returns a structured JSON response containing their serialized
        representations. Each plugin is validated by round-tripping through the Pydantic model.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments, such as filter criteria (e.g., ``name``).
        :return: A `SmarterJournaledJsonResponse` containing a list of SQL plugin manifests and metadata.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.get(request, name="my_plugin")
            print(response.data)

        :raises SAMProxyBrokerError:
            If a plugin cannot be serialized or validated
            during the retrieval process.

        .. seealso::
            :class:`Proxy`
            :class:`ProxySerializer`
            :class:`SAMProxy`
            :class:`SmarterJournaledJsonResponse`
            :class:`SmarterJournalCliCommands`
            :class:`SAMKeys`
            :class:`SAMMetadataKeys`
            :class:`SCLIResponseGet`
            :class:`SCLIResponseGetData`
        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)

        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        # generate a QuerySet of Proxy objects that match our search criteria
        if name:
            plugins = Proxy.objects.filter(user_profile__account=self.account, name=name)
        else:
            plugins = Proxy.objects.filter(user_profile__account=self.account)
        logger.debug(
            "%s.get() found %s Proxies for account %s", self.formatted_class_name, plugins.count(), self.account
        )

        model_titles = self.get_model_titles(serializer=ProxySerializer())

        # iterate over the QuerySet and use a serializer to create a model dump for each LLMClient
        for plugin in plugins:
            try:
                self.plugin_init()
                self.plugin_meta = plugin

                model_dump = ProxySerializer(plugin).data
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)

            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    plugin.name,
                    exc_info=True,
                )
                raise SAMProxyBrokerError(
                    f"Failed to serialize {self.kind} {plugin.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: model_titles,
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)
