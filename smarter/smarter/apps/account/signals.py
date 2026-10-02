"""Signals for account app."""

from django.dispatch import Signal

new_user_created = Signal()
"""
Signal sent when a new user is created.

Arguments:

    user_profile (UserProfile): The profile of the newly created user.

Example::

    new_user_created.send(sender=self.__class__, user_profile=self)
"""

new_charge_created = Signal()
"""
Signal sent when a new charge is created.

Arguments:
    charge (Charge): The newly created charge instance.

Example::

    new_charge_created.send(sender=self.__class__, charge=self)
"""

cache_invalidate = Signal()
"""
Signal sent to trigger cache invalidation.

Arguments:
    None

Example::

    cache_invalidate.send(sender=self.__class__)
"""

charge_authorized = Signal()
"""
Signal sent when a charge is authorized.

Arguments:
    record_locator (str): The record locator associated with the charge.
    charge (Charge): The charge instance that has been authorized.

Example::
    charge_authorized.send(sender=self.__class__, record_locator=self.record_locator, charge=self)
"""

charge_declined = Signal()
"""
Signal sent when a charge is declined.

Arguments:
    record_locator (str): The record locator associated with the charge.
    charge (Charge): The charge instance that has been declined.

Example::

    charge_declined.send(sender=self.__class__, record_locator=self.record_locator, charge=self)
"""

budget_warning = Signal()
"""
Signal sent when a resource's spending reaches its budget's warning threshold.

Sent once per billing period.

Arguments:
    resource_constraint (ResourceConstraint): The budget attached to the resource.
    actual (Decimal): The resource's spending, in the budget's unit.
    limit (Decimal): The limit whose threshold was reached.

Example::

    budget_warning.send(sender=self.__class__, resource_constraint=self, actual=actual, limit=limit)
"""

budget_exceeded = Signal()
"""
Signal sent when a resource's spending reaches a limit of its budget, or the budget's duration ends.

Sent once per billing period.

Arguments:
    resource_constraint (ResourceConstraint): The budget attached to the resource.
    lock (Optional[ResourceLock]): The lock that now refuses charges, or None if the budget only warns.
    reason (str): Which limit was reached.
    actual (Decimal): The resource's spending, in the budget's unit.
    limit (Decimal): The limit that was reached.

Example::

    budget_exceeded.send(sender=self.__class__, resource_constraint=self, lock=lock, reason=reason, actual=actual, limit=limit)
"""

budget_released = Signal()
"""
Signal sent when a resource's lock is removed, e.g. at the end of its billing period.

Arguments:
    resource_constraint (ResourceConstraint): The budget attached to the resource.

Example::

    budget_released.send(sender=self.__class__, resource_constraint=self)
"""
