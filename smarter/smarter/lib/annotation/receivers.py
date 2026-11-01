# pylint: disable=unused-argument
"""Django signal receivers of Smarter annotations."""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import LISTVIEW_CACHE_ALL, connect_listview_cache
from smarter.lib.django.models import MetaDataModel

from .models import Annotation, get_cached_annotations

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


@receiver(post_save, sender=Annotation, dispatch_uid=f"{__name__}.invalidate_cached_annotations.post_save")
@receiver(post_delete, sender=Annotation, dispatch_uid=f"{__name__}.invalidate_cached_annotations.post_delete")
def invalidate_cached_annotations(sender, instance: Annotation, **kwargs):
    """
    Make a resource's cached annotations stale when one of its rows is saved or deleted.

    Rows change through :meth:`~smarter.lib.annotation.models.AnnotationQuerySet.sync`, and also
    through the Django admin and direct writes, which don't go through it. Waiting for the commit
    keeps a request that reads the rows before the change commits from caching the old ones.
    """
    content_type_id, object_id = instance.content_type_id, instance.object_id
    logger.debug(
        "%s.invalidate_cached_annotations() content_type_id=%s object_id=%s",
        logger_prefix,
        content_type_id,
        object_id,
    )
    transaction.on_commit(lambda: get_cached_annotations.invalidate(content_type_id, object_id))


# the web console's lists show annotations and filter by them, and an annotation may change without
# its resource being saved, e.g. with set_annotation() or in the Django admin.
connect_listview_cache(LISTVIEW_CACHE_ALL, "annotation.Annotation")
