"""
What the platform knows about one user's problem: their account, their failed sign-ins, and their failed requests.

The MCPServer's staff-only ``user_support_snapshot`` tool
(:class:`~smarter.apps.mcpserver.protocol.tools.helpdesk.UserSupportSnapshotTool`) uses this module to answer
help desk questions about one person, such as "my login isn't working" or "my prompt says there was a
system error". :func:`support_snapshot` gathers, for one email address:

- **the account**: whether a user has the address, whether that user is active, when they joined and
  last signed in, how they can sign in (with a password, or only with Google or GitHub), and the
  Smarter accounts that they belong to (:func:`account_state`).
- **their failed sign-ins** of the last 72 hours, from the pod logs. The platform never logs the email
  address that someone typed: it logs a keyed hash of it,
  :func:`~smarter.apps.account.login_audit.login_identity`, with the reason, e.g.
  ``reason=wrong_password``. This module computes the same hash, and searches the logs for it
  (:func:`failed_sign_ins`).
- **their recent failed requests**, from the journal, which records every api call and chat prompt
  with its status code: each one with a status of 400 or more, with its error's class and description
  (:func:`failed_requests`).
- **hints**: what the findings suggest that the user can do, e.g. reset their password, or sign in
  with Google (:func:`hints`).

The snapshot is for the platform's staff. It may say that no user has an address, which a reply to the
person who asked must never repeat, so that the help desk cannot be used to find out who has an
account. See :mod:`smarter.apps.mcpserver.services.helpdesk.replies`.

Nothing is written. Each part that cannot be read, e.g. the logs in local development, where there is no
log store, is named in :attr:`SupportSnapshot.errors`, and the other parts are still returned.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from django.conf import settings
from social_django.models import UserSocialAuth

from smarter.apps.account.login_audit import LoginFailure, login_identity
from smarter.apps.account.models import User, UserProfile
from smarter.apps.infrastructure.exceptions import SmarterInfrastructureError
from smarter.apps.infrastructure.services import infrastructure
from smarter.apps.infrastructure.services.logs import LOG_RETENTION, LogQuery
from smarter.lib.journal.models import SAMJournal
from smarter.lib.typing import SmarterDictType

MAX_FAILED_REQUESTS = 15
"""The most failed requests that a snapshot lists, newest first."""

MAX_DESCRIPTION = 300
"""The most characters of a failed request's error description that a snapshot shows."""

MAX_SIGN_IN_LINES = 500
"""The most log lines of failed sign-ins that a snapshot reads."""

REASON = re.compile(r"reason=(?P<reason>[a-z_]+)")
"""The reason of a failed sign-in, in the line that :func:`~smarter.apps.account.login_audit.log_login_failure` writes."""

MULTITENANT_BACKEND = "smarter.lib.social_core.backends.multitenant.DjangoModelBackendMultitenant"
"""The sign-in backend of a hosted platform, which also requires an active subscription."""


@dataclass
class AccountState:
    """
    The state of the user who has an email address, as ``user_support_snapshot`` reports it.

    :func:`account_state` builds it from the user and their profiles.
    """

    username: str
    """The user's username."""

    is_active: bool
    """Whether the user may sign in.

    An inactive user is refused, whatever their password.
    """

    date_joined: Optional[datetime]
    """When the user signed up, in UTC."""

    last_login: Optional[datetime]
    """When the user last signed in, in UTC, or None if they never did."""

    has_password: bool
    """Whether the user has a password.

    A user who signed up with Google or GitHub has none.
    """

    social_providers: list[str] = field(default_factory=list)
    """The social sign-ins linked to the user, e.g. ``["google-oauth2", "github"]``."""

    accounts: list[str] = field(default_factory=list)
    """The Smarter accounts that the user belongs to, e.g. ``["Acme Corp (1234-5678-9012)"]``."""

    subscription_active: Optional[bool] = None
    """On a hosted platform, whether the user's subscription is active, or None if the platform has no subscriptions."""


@dataclass
class FailedRequest:
    """
    One of the user's requests that failed, from the journal, e.g. a chat prompt that answered 500.

    :func:`failed_requests` builds it from a :class:`~smarter.lib.journal.models.SAMJournal` row.
    """

    created_at: Optional[datetime]
    """When the request was made, in UTC."""

    thing: str
    """What the request was about, e.g. ``prompt``, ``LLMClient`` or ``Plugin``."""

    command: str
    """What it did, e.g. ``prompt``, ``apply`` or ``deploy``."""

    status_code: int
    """The HTTP status that it answered, e.g. 400 or 500."""

    error_class: str = ""
    """The class of the error, e.g. ``SmarterValueError``, from the response, or empty if it names none."""

    description: str = ""
    """The error's description, from the response, cut at :data:`MAX_DESCRIPTION` characters."""


@dataclass
class SupportSnapshot:
    """
    What the platform knows about one user's problem, as ``user_support_snapshot`` reports it.

    :func:`support_snapshot` builds it.
    """

    email: str
    """The email address that the snapshot is about, as the staff member gave it."""

    users_found: int = 0
    """How many users have the address.

    Normally 0 or 1.
    """

    account: Optional[AccountState] = None
    """The state of the user who has the address, or None if no user has it."""

    failed_sign_ins: dict[str, int] = field(default_factory=dict)
    """The failed sign-ins of the last 72 hours with the address, counted by reason, e.g. ``{"wrong_password": 3}``."""

    last_failed_sign_in: Optional[datetime] = None
    """When the latest failed sign-in happened, in UTC, or None if there was none."""

    failed_requests: list[FailedRequest] = field(default_factory=list)
    """The user's failed requests of the period, newest first."""

    errors: list[str] = field(default_factory=list)
    """The parts that could not be read, and why, e.g. ``sign-ins: the log store is not available``."""


def account_state(user: User) -> AccountState:
    """
    Describe a user's account: whether they can sign in, and how.

    Side effects: a query of the user's social sign-ins, a query of their profiles, and, on a hosted
    platform, a call to the Account Manager for their subscription (see :func:`subscription_active`).

    :param user: The user.
    :returns: The account's state.
    """
    providers = []
    socials = UserSocialAuth.objects.filter(user=user)
    for social in socials:
        providers.append(str(social.provider))

    accounts = []
    profiles = UserProfile.objects.filter(user=user).select_related("account")
    for profile in profiles:
        account = profile.account
        accounts.append(f"{account.company_name} ({account.account_number})")

    return AccountState(
        username=user.get_username(),
        is_active=user.is_active,
        date_joined=user.date_joined,
        last_login=user.last_login,
        has_password=user.has_usable_password(),
        social_providers=sorted(providers),
        accounts=accounts,
        subscription_active=subscription_active(user),
    )


def subscription_active(user: User) -> Optional[bool]:
    """
    Check a user's subscription, on a hosted platform that requires one to sign in.

    Only a platform whose ``AUTHENTICATION_BACKENDS`` includes :data:`MULTITENANT_BACKEND` checks
    subscriptions. Its check answers True when the Account Manager cannot be reached, so as not to lock
    users out, so True means "active, or unknown".

    Side effects: on a hosted platform, an HTTP call to the Account Manager, which its check caches.

    :param user: The user.
    :returns: Whether the subscription is active, or None if the platform has no subscriptions.
    """
    if MULTITENANT_BACKEND not in settings.AUTHENTICATION_BACKENDS:
        return None
    # pylint: disable=import-outside-toplevel
    from smarter.lib.social_core.backends.multitenant import verify_payment_status

    return verify_payment_status(user.get_username())


def failed_sign_ins(snapshot: SupportSnapshot) -> None:
    """
    Add the failed sign-ins of the last 72 hours with the snapshot's email address to the snapshot.

    The logs hold the keyed hash of the address that was typed,
    :func:`~smarter.apps.account.login_audit.login_identity`, never the address, so the search is for
    ``identity=<hash>``. Each line names its reason, e.g. ``reason=wrong_password``, which is counted.
    A log store that cannot be read is named in the snapshot's errors.

    Side effects: one query of the log store, through
    :data:`smarter.apps.infrastructure.services.infrastructure` ``.logs``.

    :param snapshot: The snapshot, whose :attr:`~SupportSnapshot.failed_sign_ins` and
        :attr:`~SupportSnapshot.last_failed_sign_in` this fills.
    """
    identity = login_identity(snapshot.email)
    query = LogQuery.last(
        LOG_RETENTION,
        components=("smarter",),
        contains=(f"identity={identity}",),
        limit=MAX_SIGN_IN_LINES,
    )
    try:
        lines = infrastructure.logs.query(query)
    except SmarterInfrastructureError as e:
        snapshot.errors.append(f"sign-ins: the log store is not available ({e})")
        return

    for line in lines:
        match = REASON.search(line.line)
        if match is None:
            continue
        reason = match.group("reason")
        count = snapshot.failed_sign_ins.get(reason, 0)
        snapshot.failed_sign_ins[reason] = count + 1
        if snapshot.last_failed_sign_in is None or line.timestamp > snapshot.last_failed_sign_in:
            snapshot.last_failed_sign_in = line.timestamp


def error_details(response: Optional[SmarterDictType]) -> tuple[str, str]:
    """
    Read the error's class and description from a journaled response.

    A failed request's response is ``{"error": {"error_class": ..., "description": ...}}`` (see
    :class:`~smarter.lib.journal.http.SmarterJournaledJsonErrorResponse`).

    :param response: The response, as the journal stored it.
    :returns: The error's class and its description, cut at :data:`MAX_DESCRIPTION` characters, each
        empty if the response does not have it.
    """
    if not isinstance(response, dict):
        return "", ""
    error = response.get("error")
    if not isinstance(error, dict):
        return "", ""
    error_class = str(error.get("error_class") or "")
    description = str(error.get("description") or "")
    return error_class, description[:MAX_DESCRIPTION]


def failed_requests(snapshot: SupportSnapshot, user: User, days: int) -> None:
    """
    Add the user's failed requests of the last days to the snapshot, newest first.

    A failed request is a journal row of the user with a status code of 400 or more: a chat prompt, or
    an api call, that answered an error.

    Side effects: one query of the journal.

    :param snapshot: The snapshot, whose :attr:`~SupportSnapshot.failed_requests` this fills.
    :param user: The user.
    :param days: How far back to read, in days.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = SAMJournal.objects.filter(user=user, status_code__gte=400, created_at__gte=since)
    rows = rows.order_by("-created_at")[:MAX_FAILED_REQUESTS]
    for row in rows:
        error_class, description = error_details(row.response)
        failed = FailedRequest(
            created_at=row.created_at,
            thing=str(row.thing),
            command=str(row.command),
            status_code=int(row.status_code),
            error_class=error_class,
            description=description,
        )
        snapshot.failed_requests.append(failed)


def support_snapshot(email: str, days: int = 7) -> SupportSnapshot:
    """
    Gather what the platform knows about one user's problem.

    The user is found by their email address, case insensitively. Their failed sign-ins are searched for
    even when no user has the address, because someone may be trying to sign in with an address that
    is mistyped, or not registered.

    Side effects: queries of the users, profiles, social sign-ins and journal, one query of the log store,
    and, on a hosted platform, a call to the Account Manager. Nothing is written.

    :param email: The email address of the person who asked for help, as staff verified it.
    :param days: How far back to read the journal, in days.
    :returns: The snapshot. A part that cannot be read is named in its ``errors``.
    """
    address = email.strip()
    snapshot = SupportSnapshot(email=address)
    users = list(User.objects.filter(email__iexact=address).order_by("id"))
    snapshot.users_found = len(users)
    failed_sign_ins(snapshot)
    if not users:
        return snapshot
    user = users[0]
    snapshot.account = account_state(user)
    failed_requests(snapshot, user, days)
    return snapshot


def hints(snapshot: SupportSnapshot) -> list[str]:
    """
    Suggest, for staff, what the findings mean, and what the user can do.

    These are for the staff member, not for the user: e.g. "no user has this address" must never be
    repeated to the person who asked (see :mod:`smarter.apps.mcpserver.services.helpdesk.replies`).

    :param snapshot: The snapshot.
    :returns: One sentence per finding that suggests something, or an empty list.
    """
    found = []
    account = snapshot.account
    reasons = snapshot.failed_sign_ins
    if account is None:
        found.append(
            "No user has this address. They may have signed up with another address, or with Google or "
            "GitHub under another address. Do not tell them whether the address has an account."
        )
    elif not account.is_active:
        found.append("The user is inactive, so every sign-in is refused. A staff member must reactivate them.")
    if account is not None and not account.has_password:
        providers = ", ".join(account.social_providers) or "a social sign-in"
        found.append(f"The user has no password: they signed up with {providers}, and must sign in with it.")
    if account is not None and account.subscription_active is False:
        found.append("The user's subscription is not active, so the platform refuses their sign-in.")
    if reasons.get(str(LoginFailure.WRONG_PASSWORD), 0) >= 3:
        found.append("Several wrong passwords: suggest that they reset their password.")
    if reasons.get(str(LoginFailure.INVALID_FORM)):
        found.append("A sign-in form was incomplete or had an invalid email address: suggest that they check it.")
    if reasons.get(str(LoginFailure.ERROR)):
        found.append(
            "A sign-in raised an error on the platform: check summarize_log_errors for the time of the sign-in."
        )
    server_errors = 0
    for request in snapshot.failed_requests:
        if request.status_code >= 500:
            server_errors += 1
    if server_errors:
        found.append(
            f"{server_errors} of their recent requests failed on the platform (status 500 or more): check "
            "platform_status and summarize_log_errors for the same times."
        )
    return found


__all__ = [
    "AccountState",
    "FailedRequest",
    "SupportSnapshot",
    "account_state",
    "failed_requests",
    "failed_sign_ins",
    "hints",
    "support_snapshot",
]
