# pylint: disable=W0718
"""Smarter API Account Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.manifest.enum import SAMAccountSpecKeys
from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.account.metadata import SAMAccountMetadata
from smarter.apps.account.manifest.models.account.model import SAMAccount
from smarter.apps.account.manifest.models.account.spec import SAMAccountSpec
from smarter.apps.account.models import Account
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)


logger = logging.getLogger(__name__)


MAX_RESULTS = 1000


class AccountSerializer(ModelSerializer):
    """Account serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = ["account_number", "company_name", "created_at", "updated_at"]


class SAMAccountBrokerError(SAMBrokerError):
    """Base exception for Smarter API Account Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Account Manifest Broker Error"


class SAMAccountBroker(AbstractBroker):
    """
    Smarter API Account Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Account manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API Account manifests. The Broker class is responsible
    for creating, updating, deleting and querying the Django ORM models, as well
    as transforming the Django ORM models into Pydantic models for serialization
    and deserialization.
    """

    # override the base abstract manifest model with the Account model
    _manifest: Optional[SAMAccount] = None
    _pydantic_model: Type[SAMAccount] = SAMAccount
    _account: Optional[Account] = None

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API Account manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()  # type: ignore
        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMAccountBrokerError(
                message=f"Invalid config dump for {self.kind} manifest: {config_dump}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.manifest is None:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        return {
            "account": self.account,
            "name": self.manifest.metadata.name,
            "description": self.manifest.metadata.description,
            "version": self.manifest.metadata.version,
            **config_dump,
        }

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API Account manifest dict.
        """
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot describe.",
                thing=self.thing,
                command=SmarterJournalCliCommands.DESCRIBE,
            )
        account_dict = model_to_dict(self.account)
        account_dict = self.snake_to_camel(account_dict)
        if not isinstance(account_dict, dict):
            raise SAMAccountBrokerError(
                message=f"Invalid account data: {account_dict}",
                thing=self.kind,
                command=SmarterJournalCliCommands.DESCRIBE,
            )
        account_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.account.account_number,
                SAMMetadataKeys.DESCRIPTION.value: self.account.company_name,
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: {
                SAMAccountSpecKeys.CONFIG.value: account_dict,
            },
            SAMKeys.STATUS.value: {
                "created": self.account.created_at.isoformat(),
                "modified": self.account.updated_at.isoformat(),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMAccountBroker()"

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMAccount]:
        """
        SAMAccount() is a Pydantic model
        that is used to represent the Smarter API Account manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader is None or not self.loader.manifest_metadata:
            return None
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        metadata = {
            **self.loader.manifest_metadata,
            "accountNumber": self.account.account_number,
        }
        spec = {
            "config": self.loader.manifest_spec,
        }
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMAccount(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMAccountMetadata(**metadata),
                spec=SAMAccountSpec(**spec),  # type: ignore
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> Type[Account]:
        return Account

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "Example_account",
                SAMMetadataKeys.DESCRIPTION.value: "an example Account manifest",
                SAMMetadataKeys.VERSION.value: "1.0.0",
                "accountNumber": self.account.account_number if self.account else None or "1234-5678-9012",
            },
            SAMKeys.SPEC.value: {
                SAMAccountSpecKeys.CONFIG.value: {
                    "companyName": self.account.company_name if self.account else None or "Humble Geniuses, Inc.",
                    "phoneNumber": self.account.phone_number if self.account else None or "617-555-1212",
                    "address1": self.account.address1 if self.account else None or "1 Main St",
                    "address2": self.account.address2 if self.account else None or "Suite 100",
                    "city": self.account.city if self.account else None or "Cambridge",
                    "state": self.account.state if self.account else None or "MA",
                    "postalCode": self.account.postal_code if self.account else None or "02139",
                    "country": self.account.country if self.account else None or "USA",
                    "language": self.account.language if self.account else None or "en-US",
                    "timezone": self.account.timezone if self.account else None or "America/New_York",
                    "currency": self.account.currency if self.account else None or "USD",
                },
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        # name: str = None, all_objects: bool = False, tags: str = None
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot get.",
                thing=self.thing,
                command=command,
            )

        # generate a QuerySet of PluginMeta objects that match our search criteria
        accounts = Account.objects.filter(id=self.account.id)  # type: ignore

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for account in accounts:
            try:
                model_dump = AccountSerializer(account).data
                if not model_dump:
                    raise SAMAccountBrokerError(
                        message=f"Model dump failed for {self.kind} {account.account_number}",
                        thing=self.kind,
                        command=command,
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error("Error in %s: %s", command, e)
                return self.json_response_err(command=command, e=e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: self.account.account_number,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=AccountSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        readonly_fields = ["id", "created_at", "updated_at", "account_number"]
        if self.account is None:
            raise SAMBrokerErrorNotReady(
                f"Account not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=command,
            )
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.account, key, value)
            self.account.save()
        except Exception as e:
            raise SAMBrokerError(message=f"Error in {command}: {e}", thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data={})

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.account:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMBrokerError(message=f"Error in {command}: {str(e)}", thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No account found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Delete not implemented", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
