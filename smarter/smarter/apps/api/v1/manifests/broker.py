"""Smarter API Manifest Abstract Broker class."""

from abc import ABC, abstractmethod

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import account_admin_user
from smarter.lib.django.user import UserType
from smarter.lib.django.validators import SmarterValidator

from .loader import SAMLoader
from .models import AbstractSAMBase


class AbstractBroker(ABC):
    """
    Smarter API Manifest Broker abstract base class. This class is responsible
    for:
    - loading, and partially validating and parsing a Smarter Api yaml manifest,
      sufficient to enable us to initialize a Pydantic model.
    - implementing the broker service pattern for the underlying object
    - initializing the corresponding Pydantic models.
    - instantiating the underlying Python object

    AbstractBroker defines the broker pattern that provides the generic services
    for the manifest: get, post, put, delete, patch.
    """

    _account: Account = None
    _user: UserType = None
    _user_profile: UserProfile = None
    _loader: SAMLoader = None
    _manifest: AbstractSAMBase = None

    def __init__(
        self,
        account_number: str,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        SmarterValidator.validate_account_number(account_number)
        self._account = Account.objects.get(account_number=account_number)

        # load, validate and parse the manifest into json
        self._loader = SAMLoader(account_number=account_number, manifest=manifest, file_path=file_path, url=url)

    ###########################################################################
    # Abstract Properties
    ###########################################################################
    @property
    @abstractmethod
    def manifest(self) -> AbstractSAMBase:
        """
        The Pydantic model representing the manifest. This is a reference
        implementation of the abstract property, for documentation purposes
        to illustrate the correct way to initialize a AbstractSAMBase Pydantic model.
        The actual property must be implemented by the concrete broker class.
        """
        if self._manifest:
            return self._manifest
        self._manifest = AbstractSAMBase(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=self.loader.manifest_metadata,
            spec=self.loader.manifest_spec,
            status=self.loader.manifest_status,
        )
        return self._manifest

    @abstractmethod
    def get(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def post(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def put(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def patch(self) -> dict:
        raise NotImplementedError

    ###########################################################################
    # Class Instance Properties
    ###########################################################################
    @property
    def loader(self) -> SAMLoader:
        return self._loader

    @property
    def account(self) -> Account:
        return self._account

    @property
    def user(self) -> UserType:
        if self._user:
            return self._user
        self._user = account_admin_user(self.manifest.metadata.account)
        return self._user

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile:
            return self._user_profile
        self._user_profile = UserProfile.objects.get(user=self.user, account=self.account)
        return self._user_profile
