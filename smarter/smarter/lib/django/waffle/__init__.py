"""
smarter.lib.django.waffle
------------------------------

Enhanced, managed Django-waffle wrapper with short-lived Redis-based caching
and database readiness checks.

Features:

- Caching: Integrates short-lived Redis-based caching to optimize feature flag (switch) checks.
- Database Readiness Handling: Implements safeguards to prevent errors when the database is not ready.
- Feature Flag Management: Centralized mechanism to check if a feature flag (switch) is active.
- Custom Django Admin: Customized Django Admin class for managing waffle switches.
- Fixed Set of Switches: Defines a fixed set of waffle switches for the Smarter API.

.. important::

    These are managed feature flags; add any new switches to the SmarterWaffleSwitches class. These switches
    are verified duing deployments to ensure that they exist in the database. Missing switches are
    automatically created with a default inactive state.

.. important::

    django-waffle relies on database tables as well as Redis for storing and caching feature flags. If the database is not ready, waffle switch values
    will default to inactive (False) to prevent application errors.

Example:
    .. code-block:: python

        from smarter.lib.django.waffle import switch_is_active

        if switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING):
            print("API logging is enabled.")

Dependencies:

- `django-waffle <https://waffle.readthedocs.io/en/stable/>`_
- `django-redis <https://django-redis.readthedocs.io/en/stable/>`_
- `Redis <https://redis.io/documentation>`_
- `Django <https://docs.djangoproject.com/en/stable/>`_
"""

from typing import TYPE_CHECKING

from .is_active import switch_is_active
from .ready import is_database_ready
from .switches import SmarterWaffleSwitches, smarter_waffle_switches

if TYPE_CHECKING:
    from .admin import SmarterSwitchAdmin


# pylint: disable=C0415
def __getattr__(name):
    """
    Lazy import of attributes to avoid circular imports and unnecessary imports at the module level.
    """
    if name == "SmarterSwitchAdmin":
        from .admin import SmarterSwitchAdmin

        return SmarterSwitchAdmin
    if name == "switch_is_active":
        return switch_is_active
    if name == "is_database_ready":
        return is_database_ready
    if name == "SmarterWaffleSwitches":
        return SmarterWaffleSwitches
    if name == "smarter_waffle_switches":
        return smarter_waffle_switches
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SmarterWaffleSwitches",
    "SmarterSwitchAdmin",
    "switch_is_active",
    "is_database_ready",
    "smarter_waffle_switches",
]
