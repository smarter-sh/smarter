"""
Signals of the llmhost app.

They are sent by :class:`smarter.apps.llmhost.services.LLMHostService` at each step of an
LLMHost's lifecycle. Each has the arguments ``llmhost`` (LLMHost), plus those listed.

Example::

    from django.dispatch import receiver
    from smarter.apps.llmhost.signals import llmhost_status_changed

    @receiver(llmhost_status_changed)
    def notify(sender, llmhost, old_status, new_status, **kwargs):
        ...
"""

from django.dispatch import Signal

llmhost_launched = Signal()
"""Sent when an LLMHost's Kubernetes resources are applied.

Arguments: llmhost, resources (list[dict]).
"""

llmhost_launch_failed = Signal()
"""Sent when an LLMHost cannot be launched.

Arguments: llmhost, error (str).
"""

llmhost_status_changed = Signal()
"""Sent when a status check changes an LLMHost's status.

Arguments: llmhost, old_status, new_status, observation.
"""

llmhost_destroyed = Signal()
"""Sent when an LLMHost's Kubernetes resources are deleted.

Arguments: llmhost, purge (bool).
"""
