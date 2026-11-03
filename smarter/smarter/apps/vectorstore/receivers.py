# pylint: disable=unused-argument
"""Receivers of the vectorstore app."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.lib import logging
from smarter.lib.django.listview import connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import VectorstoreMeta
from .signals import (
    document_load_failed,
    document_loaded,
    vectorstore_deployed,
    vectorstore_destroyed,
    vectorstore_status_changed,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING, SmarterWaffleSwitches.VECTORSTORE_LOGGING]
)
module_prefix = logging.SmarterFormattedText.text(__name__)


@receiver(post_save, sender=VectorstoreMeta)
@receiver(post_delete, sender=VectorstoreMeta)
def vectorstore_changed(sender, instance: VectorstoreMeta, **kwargs):
    """
    Invalidate the cached vectorstore, and its owner's cached lists.

    :param sender: The model class.
    :param instance: The vectorstore that was saved or deleted.
    """
    # pylint: disable=import-outside-toplevel
    from .caching import invalidate_all_cached_vectorstores_for_user_profile

    try:
        # invalidating re-reads it, which a deleted vectorstore cannot be.
        VectorstoreMeta.get_cached_object(invalidate=True, pk=instance.pk)
    except VectorstoreMeta.DoesNotExist:
        pass
    if instance.user_profile_id:  # type: ignore[attr-defined]
        invalidate_all_cached_vectorstores_for_user_profile(instance.user_profile)


@receiver(vectorstore_deployed)
def vectorstore_deployed_receiver(sender, vectorstore: VectorstoreMeta, **kwargs):
    """
    Log that a vectorstore was deployed.

    :param sender: The sender's class.
    :param vectorstore: The vectorstore.
    """
    logger.info("%s Vectorstore %s deployed.", module_prefix, vectorstore)


@receiver(vectorstore_destroyed)
def vectorstore_destroyed_receiver(sender, vectorstore: VectorstoreMeta, **kwargs):
    """
    Log that a vectorstore's database was destroyed.

    :param sender: The sender's class.
    :param vectorstore: The vectorstore.
    """
    logger.info("%s Vectorstore %s destroyed.", module_prefix, vectorstore)


@receiver(vectorstore_status_changed)
def vectorstore_status_changed_receiver(sender, vectorstore: VectorstoreMeta, previous, status, message, **kwargs):
    """
    Log a vectorstore's change of status, at warning level when it failed.

    :param sender: The sender's class.
    :param vectorstore: The vectorstore.
    :param previous: Its previous status.
    :param status: Its new status.
    :param message: Why.
    """
    log = logger.warning if status == "failed" else logger.info
    log("%s Vectorstore %s: %s -> %s %s", module_prefix, vectorstore, previous, status, message)


@receiver(document_loaded)
def document_loaded_receiver(sender, document, **kwargs):
    """
    Log that a document was loaded, and its number of chunks.

    :param sender: The sender's class.
    :param document: The document.
    """
    logger.info("%s %s loaded, %s chunks.", module_prefix, document, document.chunk_count)


@receiver(document_load_failed)
def document_load_failed_receiver(sender, document, error, **kwargs):
    """
    Log that a document could not be loaded.

    :param sender: The sender's class.
    :param document: The document.
    :param error: Why.
    """
    logger.warning("%s %s failed to load: %s", module_prefix, document, error)


# the list view's cached pages are stale when the resources that it shows change. See smarter.lib.django.listview.
connect_listview_cache(
    "Vectorstore",
    "vectorstore.VectorstoreMeta",
    "vectorstore.VectorstoreDocument",
    "vectorstore.VectorstoreSnapshot",
    "vectorsearch.Vectorsearch",
)
