# pylint: disable=W0718
"""Smarter API Account Manifest handler"""

import logging

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.manifest.enum import SAMAccountSpecKeys
from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.account.model import SAMAccount
from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.common.api import SmarterApiVersions
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
from smarter.lib.manifest.loader import SAMLoader


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
    def get_readable_name(self):
        return "Smarter API Account Manifest Broker Error"


class SAMAccountBroker(AbstractBroker, AccountMixin):
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
    _manifest: SAMAccount = None
    _account: Account = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        account: Account,
        api_version: str = SmarterApiVersions.V1.value,
        name: str = None,
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        """
        Load, validate and parse the manifest. The parent will initialize
        the generic manifest loader class, SAMLoader(), which can then be used to
        provide initialization data to any kind of manifest model. the loader
        also performs cursory high-level validation of the manifest, sufficient
        to ensure that the manifest is a valid yaml file and that it contains
        the required top-level keys.
        """
        super().__init__(
            request=request,
            api_version=api_version,
            account=account,
            name=name,
            kind=kind,
            loader=loader,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API Account manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
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
        account_dict = model_to_dict(self.account)
        account_dict = self.snake_to_camel(account_dict)
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
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMAccount:
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
        if self.loader:
            self._manifest = SAMAccount(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata={
                    **self.loader.manifest_metadata,
                    "accountNumber": self.account.account_number,
                },
                spec={
                    "config": self.loader.manifest_spec,
                },
                status=self.loader.manifest_status,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> Account:
        return Account

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "ExampleAccount",
                SAMMetadataKeys.DESCRIPTION.value: "an example Account manifest",
                SAMMetadataKeys.VERSION.value: "1.0.0",
                "accountNumber": self.account.account_number,
            },
            SAMKeys.SPEC.value: {
                SAMAccountSpecKeys.CONFIG.value: {
                    "companyName": self.account.company_name or "Humble Geniuses, Inc.",
                    "phoneNumber": self.account.phone_number or "617-555-1212",
                    "address1": self.account.address1 or "1 Main St",
                    "address2": self.account.address2 or "Suite 100",
                    "city": self.account.city or "Cambridge",
                    "state": self.account.state or "MA",
                    "postalCode": self.account.postal_code or "02139",
                    "country": self.account.country or "USA",
                    "language": self.account.language or "en-US",
                    "timezone": self.account.timezone or "America/New_York",
                    "currency": self.account.currency or "USD",
                },
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        # name: str = None, all_objects: bool = False, tags: str = None
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []

        # generate a QuerySet of PluginMeta objects that match our search criteria
        accounts = Account.objects.filter(id=self.account.id)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for account in accounts:
            try:
                model_dump = AccountSerializer(account).data
                if not model_dump:
                    raise SAMAccountBrokerError(
                        message=f"Model dump failed for {self.kind} {account.name}", thing=self.kind, command=command
                    )
                data.append(model_dump)
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

    def apply(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
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

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.account:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMBrokerError(message=f"Error in {command}: {str(e)}", thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No account found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Delete not implemented", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
