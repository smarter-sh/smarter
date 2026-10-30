# pylint: disable=unused-argument
"""Django signal receivers of Smarter annotations."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import LISTVIEW_CACHE_ALL, invalidate_listview_cache
from smarter.lib.django.models import MetaDataModel

from .models import Annotation
from .signals import annotations_changed

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


@receiver(post_delete)
def delete_annotations(sender, instance, **kwargs):
    """
    Delete a resource's annotations when the resource is deleted.

    Annotations point at their resource through a content type, not a foreign key, so the database
    doesn't cascade the deletion.
    """
    if not isinstance(instance, MetaDataModel) or instance.pk is None:
        return
    changes = Annotation.objects.delete_for_object(instance)
    if changes:
        logger.debug(
            "%s.delete_annotations() deleted %s annotations of %s %s",
            logger_prefix,
            len(changes),
            sender.__name__,
            instance.pk,
        )


@receiver(annotations_changed, dispatch_uid=f"{__name__}.invalidate_listviews")
def invalidate_listviews(sender, **kwargs):
    """
    Make every list's cached pages stale when a resource's annotations change.

    The web console's lists show annotations and filter by them. A change may be made without
    saving the resource, e.g. with ``set_annotation()``, so the resource's own ``post_save`` can't be
    relied on.
    """
    invalidate_listview_cache(LISTVIEW_CACHE_ALL)
