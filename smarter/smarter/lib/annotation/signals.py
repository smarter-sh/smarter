"""Signals of Smarter annotations."""

from django.dispatch import Signal

annotations_changed = Signal()
"""
Sent after a transaction that added, changed or removed a resource's annotations commits.

Keyword arguments:

- ``sender``: the resource's model class.
- ``instance``: the resource.
- ``object_id``: the resource's primary key, which survives the resource's deletion.
- ``changes``: a list of :class:`smarter.lib.annotation.contract.AnnotationChange`.
- ``resource_deleted``: True when the annotations were removed because the resource was deleted.

Receivers that care about one integration's keys should register an annotation handler instead
(:func:`smarter.lib.annotation.handlers.annotation_handler`), which is called with that prefix's
changes only.
"""

__all__ = ["annotations_changed"]
