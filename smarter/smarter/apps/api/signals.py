"""Signals for api app."""

from django.dispatch import Signal


api_request_initiated = Signal()
api_request_completed = Signal()
api_request_failed = Signal()
