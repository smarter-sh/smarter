"""Account serializers for Smarter API."""

from collections.abc import Iterable, MutableMapping
from typing import List, Optional, Set

from rest_framework import serializers

from smarter.apps.account.models import (
    Account,
    AccountContact,
    Budget,
    User,
    UserProfile,
)
from smarter.lib import logging
from smarter.lib.django.serializers import MetaDataModelSerializer
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

logger = logging.getLogger(__name__)


class UserSerializer(MetaDataModelSerializer):
    """
    Serializer for the `User` model in the Smarter API.

    This serializer converts Django `User` model instances to and from JSON using camelCase field names,
    making it suitable for API responses and requests.

    :param id: Integer. The unique identifier for the user.
    :param username: String. The user's username.
    :param first_name: String. The user's first name.
    :param last_name: String. The user's last name.
    :param email: String. The user's email address.
    :param is_staff: Boolean. Indicates if the user has staff privileges.
    :param is_superuser: Boolean. Indicates if the user has superuser privileges.

    .. note::

           All fields listed in ``fields`` are included in serialization. Add more fields to the list if needed.

    **Example usage**::

        from smarter.apps.account.serializers import UserSerializer
        serializer = UserSerializer(user_instance)
        data = serializer.data
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_superuser",
        ]  # add more fields if needed


class UserMiniSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for a minimal representation of the `User` model in the Smarter API.

    This serializer is designed for use cases where only essential user information is required,
    such as listing users or embedding user data in related resources.

    :param username: String. The user's username.
    :param email: String. The user's email address.

    .. note::

            All fields are read-only and included in the serialized output.

    .. tip::

            Use this serializer for lightweight API responses to reduce payload size.

    **Example usage**::

        from smarter.apps.account.serializers import UserMiniSerializer
        serializer = UserMiniSerializer(user_instance)
        data = serializer.data

    .. seealso::
        For full user details, use :class:`UserSerializer`.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
            "email",
        ]

        read_only_fields = fields


class AccountSerializer(MetaDataModelSerializer):
    """
    Serializer for the `Account` model in the Smarter API.

    This serializer provides full access to all fields of the `Account` model, making it suitable for
    detailed account data retrieval and updates via API endpoints.

    :param account_number: String. The unique identifier for the account.
    :param name: String. The account name.
    :param ...: Other fields as defined in the `Account` model.

    .. important::

            All fields in the `Account` model are included in serialization and deserialization.

    **Example usage**::

        from smarter.apps.account.serializers import AccountSerializer
        serializer = AccountSerializer(account_instance)
        data = serializer.data

    .. seealso::
        For lightweight account representations, use :class:`AccountMiniSerializer`.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = "__all__"


class BudgetSerializer(MetaDataModelSerializer):
    """
    Serializer for the :class:`Budget` model, with the number of resources it is attached to, and of those it locks.

    **Example usage**::

        from smarter.apps.account.serializers import BudgetSerializer
        data = BudgetSerializer(budget).data
    """

    resources = serializers.SerializerMethodField()
    locked = serializers.SerializerMethodField()
    manifest_url = serializers.SerializerMethodField()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Budget
        fields = "__all__"

    def get_resources(self, obj: Budget) -> int:
        return obj.constraints.filter(is_active=True).count()  # type: ignore[attr-defined]

    def get_manifest_url(self, obj: Budget) -> str:
        """The URL of the Budget's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from django.urls import reverse

        from smarter.apps.account.views.budget.urls import BudgetReverseNames

        return reverse(
            f"{BudgetReverseNames.namespace}:{BudgetReverseNames.detailview}", kwargs={"hashed_id": obj.hashed_id}
        )

    def get_locked(self, obj: Budget) -> int:
        return obj.constraints.filter(is_active=True, locks__isnull=False).distinct().count()  # type: ignore[attr-defined]


class AccountMiniSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for a minimal representation of the `Account` model in the Smarter API.

    This serializer is intended for scenarios where only the account number is required, such as embedding
    account references in related resources or optimizing API payload size.

    :param account_number: String. The unique identifier for the account.

    .. note::

            Only the ``account_number`` field is included in serialization.

    .. tip::

            Use this serializer for nested relationships or summary views.

    **Example usage**::

        from smarter.apps.account.serializers import AccountMiniSerializer
        serializer = AccountMiniSerializer(account_instance)
        data = serializer.data

    .. seealso::
        For full account details, use :class:`AccountSerializer`.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Account
        fields = ("account_number",)


class UserProfileSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `UserProfile` model in the Smarter API.

    This serializer provides a minimal representation of a user profile, including nested user and account data.
    Use it for endpoints where a summary of user and account relationships is required.

    :param user: Instance of :class:`UserMiniSerializer`. Minimal user information.
    :param account: Instance of :class:`AccountMiniSerializer`. Minimal account information.

    .. note::

            Only the ``user`` and ``account`` fields are included in serialization.

    **Example usage**::

        from smarter.apps.account.serializers import UserProfileSerializer
        serializer = UserProfileSerializer(profile_instance)
        data = serializer.data

    .. seealso::
        For more detailed user or account data, use :class:`UserSerializer` or :class:`AccountSerializer`.
    """

    user = UserMiniSerializer()
    account = AccountMiniSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = UserProfile
        fields = (
            "user",
            "account",
        )


class AccountContactSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the `AccountContact` model in the Smarter API.

    This serializer exposes all fields of the `AccountContact` model, including a minimal account reference.
    Use it for endpoints that manage or display account contact information.

    :param account: Instance of :class:`AccountMiniSerializer`. Minimal account information.
    :param ...: All other fields as defined in the `AccountContact` model.

    .. note::

            All fields are read-only in this serializer.

    **Example usage**::

        from smarter.apps.account.serializers import AccountContactSerializer
        serializer = AccountContactSerializer(contact_instance)
        data = serializer.data

    .. seealso::

            For full account details, use :class:`AccountSerializer`.
    """

    account = AccountMiniSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = AccountContact
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


def user_can_delete(obj, kind: Optional[str], user: object, owned_pks: Optional[Set] = None) -> bool:
    """
    Return True if a user may delete a resource now.

    The user must have ownership permission for the resource, as in
    :meth:`MetaDataWithOwnershipModelManager.with_ownership_permission_for`, and no other resource may
    depend on it, as in :meth:`AbstractBroker.has_dependents`. It is the ``canDelete`` of the
    resource's api responses, e.g. :meth:`MetaDataWithOwnershipModelSerializer.get_can_delete`.

    .. note::

        A resource list calls this for every row that it shows, so it builds no broker: it asks
        the broker class whether any resource depends on this one, with a few ``EXISTS`` queries.

    :param obj: The resource.
    :type obj: MetaDataWithOwnershipModel
    :param kind: The resource's SAM kind, e.g. LLMClient, which finds its broker.
    :type kind: Optional[str]
    :param user: The user, e.g. the request's user. Anything that is not a :class:`User`, e.g. an
        anonymous user or None, may delete nothing.
    :type user: object
    :param owned_pks: The primary keys of the resources that the user has ownership permission for,
        among those of a list's page, so that a page asks once rather than once per row. None asks
        the database for this resource alone.
    :type owned_pks: Optional[Set]
    :return: Whether the user may delete the resource.
    :rtype: bool
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.brokers import Brokers

    broker_class = Brokers.get_broker(kind) if kind else None
    if broker_class is None or not isinstance(user, User):
        return False
    if owned_pks is not None:
        if obj.pk not in owned_pks:
            return False
    elif not type(obj).objects.with_ownership_permission_for(user).filter(pk=obj.pk).exists():
        return False
    try:
        return not broker_class.has_dependents(obj)
    # e.g. a broker that does not implement dependents(). pylint: disable=W0718
    except Exception as e:
        logger.warning(
            "%s.user_can_delete() could not check the dependencies of %s %s: %s", __name__, kind, obj.name, e
        )
        return False


class MetaDataWithOwnershipModelSerializer(MetaDataModelSerializer):
    """Serializer for models that extend MetaDataWithOwnershipModel, adding an 'account' field.

    It also adds ``can_delete``, which is True if the authenticated user may delete the resource
    now: they have ownership permission for it, and no other resource depends on it. Subclasses
    set ``Meta.kind`` to the resource's SAM kind, which ``can_delete`` needs to find its broker.

    It also adds ``detail_url``, the url of the resource's detail
    (:class:`smarter.apps.dashboard.views.views.api.resource_detail.ResourceDetailView`): its manifest,
    the resources that it uses, and those that use it, which a web console list shows when one of its
    rows is chosen. Every subclass includes both, whatever its ``Meta.fields``.
    """

    user_profile = UserProfileSerializer(read_only=True)
    can_delete = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataModelSerializer.Meta):
        fields = "__all__"
        read_only_fields = getattr(MetaDataModelSerializer.Meta, "read_only_fields", [])

        # mcdaniel apr-2026: this is an abstract base serializer. if i understand this
        # correctly, the child serializers will override the Meta class and thus this will not be used.
        # and at any rate, setting the model there it seems to break Sphinx.
        # ----------------------------------------------------------------------------------------
        # model = MetaDataModel
        # abstract = True

    def get_field_names(self, declared_fields, info) -> List[str]:
        """
        Return the field names to serialize, always including ``can_delete`` and ``detail_url``.

        DRF omits an inherited declared field from a subclass whose ``Meta.fields`` is a list
        that does not name it, so they are added here for every subclass.
        """
        field_names = list(super().get_field_names(declared_fields, info))
        for name in ("can_delete", "detail_url"):
            if name not in field_names:
                field_names.append(name)
        return field_names

    def kind_of(self, obj) -> Optional[str]:
        """
        Return the resource's SAM kind: the serializer's ``Meta.kind``, or the resource's own ``kind``, as a plugin has.

        :param obj: The resource.
        :type obj: MetaDataWithOwnershipModel
        :return: The kind, e.g. ``Guardrail``, or None if neither says.
        :rtype: Optional[str]
        """
        obj_kind = getattr(obj, "kind", None)
        return getattr(self.Meta, "kind", None) or getattr(obj_kind, "value", obj_kind)

    def get_detail_url(self, obj) -> Optional[str]:
        """
        Return the url of the resource's detail, from its kind and record locator.

        :param obj: The resource.
        :type obj: MetaDataWithOwnershipModel
        :return: The url, e.g. ``/dashboard/api/resource/Guardrail/guardrail-rMTAwx/``, or None if the
            serializer does not know the resource's kind, or the resource has no record locator.
        :rtype: Optional[str]
        """
        # the dashboard's resource detail imports the brokers, which import this module.
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import resource_detail_url

        return resource_detail_url(self.kind_of(obj), getattr(obj, "record_locator", None))

    def get_can_delete(self, obj) -> bool:
        """
        Return True if the authenticated user may delete the resource now.

        The user can delete the object if a.) they have permission and b.)
        no dependencies existing on the object based on the SAMBroker
        enforcement rules.

        The user must have ownership permission for the resource, as in
        :meth:`MetaDataWithOwnershipModelManager.with_ownership_permission_for`, and no other
        resource may depend on it, as in :meth:`AbstractBroker.has_dependents`.

        :param obj: The resource.
        :type obj: MetaDataWithOwnershipModel
        :return: Whether the user may delete the resource. False if the serializer has no request in
            its context, or does not know the resource's kind. See :func:`user_can_delete`.
        :rtype: bool
        """
        request = self.context.get("request")
        user = getattr(request, "user", None) if request is not None else None
        return user_can_delete(obj, self.kind_of(obj), user, owned_pks=self._owned_pks_of_page(obj, user))

    def _owned_pks_of_page(self, obj, user) -> Optional[Set]:
        """
        Return the primary keys of the rows of a list's page that the user has ownership permission for.

        When this serializer is the child of a list serializer (``many=True``), it asks the database
        once for every row of the page, and keeps the answer in the shared serializer context.
        Otherwise it returns None, and :func:`user_can_delete` asks for the one resource.

        :param obj: The resource being serialized.
        :param user: The request's user.
        :return: The primary keys, or None.
        """
        parent = self.parent
        rows: Iterable = ()
        if isinstance(parent, serializers.ListSerializer) and isinstance(parent.instance, Iterable):
            rows = parent.instance
        else:
            return None
        if not isinstance(user, User):
            return None
        cache_key = f"_owned_pks.{type(obj).__module__}.{type(obj).__qualname__}.{user.pk}"
        context = self.context
        owned_pks = context.get(cache_key)
        if owned_pks is None:
            pks = [row.pk for row in rows if isinstance(row, type(obj))]
            owned_pks = set(
                type(obj).objects.with_ownership_permission_for(user).filter(pk__in=pks).values_list("pk", flat=True)
            )
            # the root serializer's context is a dict, shared by every row of the page.
            if isinstance(context, MutableMapping):
                context[cache_key] = owned_pks
        return owned_pks
