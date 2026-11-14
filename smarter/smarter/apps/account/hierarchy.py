"""
The account hierarchy, and the resources that it shares.

Accounts form a tree (:doc:`ADR-036 </adr/036-account-hierarchy>`). Each :class:`~smarter.apps.account.models.Account`
has a ``parent``, and the Smarter account is the root: an account whose ``parent`` is null is directly under
it. Separately from the tree, an account's ``share_scope`` names the audience of its resources: itself or one of
its ancestors, whose whole subtree may then read them. Null means that the account shares nothing.

A user profile may read the resources of an account X if the profile's account is X, or descends from
``X.share_scope``. This module computes that list of accounts, nearest first, caches it, and resolves a
resource's name against it.

.. code-block:: python

    from smarter.apps.account.hierarchy import readable_account_ids, resolve_by_name

    account_ids = readable_account_ids(user_profile.account_id)
    connection = resolve_by_name(SqlConnection.objects, "stackademy_hr", user_profile)
"""

from typing import TYPE_CHECKING, Optional, TypeVar

from cache_results import cache_results

from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

if TYPE_CHECKING:
    from smarter.apps.account.models import (
        MetaDataWithOwnershipModel,
        SmarterQuerySetWithPermissions,
        UserProfile,
    )

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

MAX_ACCOUNT_TREE_DEPTH = 32
"""
The deepest that the account tree may be.

An organization's chart is a handful of levels deep. The limit guards the walk up the tree against a cycle
that a direct database edit could create.
"""

READABLE_ACCOUNTS_CACHE_TIMEOUT = 60 * 60
"""
How long, in seconds, an account's readable accounts are cached.

:class:`~smarter.apps.account.models.Account` invalidates them whenever the tree or its sharing changes, so the
timeout only bounds how long a direct database edit that bypasses ``Account.save()`` goes unnoticed.
"""

_RT = TypeVar("_RT", bound="MetaDataWithOwnershipModel")


def root_account_id() -> Optional[int]:
    """
    The id of the root of the account tree, the Smarter account.

    :returns: The Smarter account's id, or None if this platform has not created it yet.
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import Account

    try:
        root = Account.get_cached_object(account_number=SMARTER_ACCOUNT_NUMBER)
    except Account.DoesNotExist:
        return None
    if root is None:
        return None
    return root.pk


def ancestor_ids(account_id: int) -> list[int]:
    """
    The account and its ancestors, nearest first, ending with the root.

    It reads the database, not the cache, so that :meth:`Account.save` can validate a change to the tree
    against the tree as it is.

    :param account_id: The account's id.
    :returns: ``[account_id, parent_id, grandparent_id, ..., root_id]``. An account whose ``parent`` is null
        is directly under the root. The root's own list is ``[root_id]``.
    :raises ValueError: if the walk up the tree meets an account twice, or goes deeper than
        :data:`MAX_ACCOUNT_TREE_DEPTH`.
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import Account

    retval: list[int] = []
    current_id: Optional[int] = account_id
    while current_id is not None:
        if current_id in retval:
            raise ValueError(f"The account tree has a cycle at account id {current_id}.")
        if len(retval) >= MAX_ACCOUNT_TREE_DEPTH:
            raise ValueError(
                f"The account tree is deeper than {MAX_ACCOUNT_TREE_DEPTH} levels at account id {account_id}."
            )
        retval.append(current_id)
        current_id = Account.objects.filter(pk=current_id).values_list("parent_id", flat=True).first()

    root_id = root_account_id()
    if root_id is not None and root_id not in retval:
        retval.append(root_id)
    return retval


@cache_results(timeout=READABLE_ACCOUNTS_CACHE_TIMEOUT)
def readable_account_ids(account_id: int) -> tuple[int, ...]:
    """
    The accounts whose resources a member of this account may read, nearest first.

    The account itself comes first. Then each account whose ``share_scope`` is this account or one of its
    ancestors, ordered by how near that ``share_scope`` is: an IT department that shares with its company
    comes before the Smarter account, which shares with everyone. Ties go to the lower id, so that the order
    is stable.

    Cached until :func:`invalidate_readable_account_ids`, which :class:`Account` calls whenever the tree or
    its sharing changes.

    :param account_id: The account's id.
    :returns: The ids of the readable accounts, nearest first.
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import Account

    ancestors = ancestor_ids(account_id)
    sharing_accounts = Account.objects.filter(share_scope_id__in=ancestors).values_list("pk", "share_scope_id")

    ranked: list[tuple[int, int]] = []
    for sharing_account_id, share_scope_id in sharing_accounts:
        if sharing_account_id == account_id:
            continue
        distance = ancestors.index(share_scope_id)
        ranked.append((distance, sharing_account_id))
    ranked.sort()

    retval = [account_id]
    for _, sharing_account_id in ranked:
        retval.append(sharing_account_id)

    logger.debug(
        "%s.readable_account_ids() account id %s may read the resources of %s accounts.",
        logger_prefix,
        account_id,
        len(retval),
    )
    return tuple(retval)


def invalidate_readable_account_ids() -> None:
    """
    Forget every account's readable accounts.

    A change to one account's ``parent`` or ``share_scope`` can change what the members of any other account
    may read, so every entry goes. The tree changes rarely, so this is cheap enough.
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import Account

    account_ids = list(Account.objects.values_list("pk", flat=True))
    for account_id in account_ids:
        readable_account_ids.invalidate(account_id)  # type: ignore
    logger.debug(
        "%s.invalidate_readable_account_ids() invalidated %s accounts.",
        logger_prefix,
        len(account_ids),
    )


def resolve_by_name(queryset: "SmarterQuerySetWithPermissions[_RT]", name: str, user_profile: "UserProfile") -> _RT:
    """
    The resource that a user profile means by ``name``, in its account tree.

    Nearest wins: the profile's own resource, else its account's, else that of the nearest account that shares
    with it (:func:`readable_account_ids`). Ties go to the most recently updated.

    Only the profile's own account tree counts, never what the user may read otherwise. A superuser reads every
    account, and a user with profiles in several accounts reads all of them, but a resource that names another,
    e.g. an HR department's plugin that names a Connection, must find the same one whoever wrote it. Otherwise
    the members of HR would read, through the plugin, whatever its author can.

    :param queryset: The resources of one kind, e.g. ``SqlConnection.objects``.
    :param name: The resource's name.
    :param user_profile: The profile that names it, e.g. a plugin's owner.
    :returns: The resource.
    :raises DoesNotExist: the model's own, if no account in the profile's tree has a resource of that name.
    """
    model = queryset.model
    readable = readable_account_ids(user_profile.account_id)  # type: ignore[attr-defined]
    candidates = queryset.filter(name=name, user_profile__account_id__in=readable).select_related("user_profile")
    candidates = model.restrict_readable(candidates, user_profile.user)
    matches = list(candidates)
    if not matches:
        raise model.DoesNotExist(f"{model.__name__} {name} does not exist, or is not shared with you.")

    def precedence(resource: _RT) -> tuple[int, float]:
        owner_account_id = resource.user_profile.account_id  # type: ignore[attr-defined]
        if resource.user_profile_id == user_profile.pk:  # type: ignore[attr-defined]
            rank = 0
        else:
            rank = readable.index(owner_account_id) + 1
        updated_at = 0.0
        if resource.updated_at:
            updated_at = resource.updated_at.timestamp()
        return rank, -updated_at

    retval = min(matches, key=precedence)
    logger.debug(
        "%s.resolve_by_name() %s %s resolved to id %s, owned by account id %s.",
        logger_prefix,
        model.__name__,
        name,
        retval.pk,
        retval.user_profile.account_id,  # type: ignore[attr-defined]
    )
    return retval


__all__ = [
    "MAX_ACCOUNT_TREE_DEPTH",
    "READABLE_ACCOUNTS_CACHE_TIMEOUT",
    "ancestor_ids",
    "invalidate_readable_account_ids",
    "readable_account_ids",
    "resolve_by_name",
    "root_account_id",
]
