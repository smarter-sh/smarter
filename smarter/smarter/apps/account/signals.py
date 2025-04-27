"""Signals for account app."""

from django.dispatch import Signal


new_user_created = Signal()
new_charge_created = Signal()
secret_created = Signal()
secret_edited = Signal()
secret_ready = Signal()
secret_deleted = Signal()
