# pylint: disable=W0613,C0115
"""Signals for Provider app."""

from django.dispatch import Signal


model_verification_requested = Signal()
model_verification_success = Signal()
model_verification_failure = Signal()

provider_verification_requested = Signal()
provider_verification_success = Signal()
provider_verification_failure = Signal()

provider_suspended = Signal()
provider_unsuspended = Signal()

provider_deprecated = Signal()
provider_undeprecated = Signal()

provider_activated = Signal()
provider_deactivated = Signal()

provider_flagged = Signal()
provider_unflagged = Signal()
