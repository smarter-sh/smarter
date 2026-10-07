"""
Signals of the vectorstore app.

Their receivers log them. Use them, e.g., to notify the owner of a failed document.
"""

from django.dispatch import Signal

vectorstore_deployed = Signal()
"""
Sent when a vectorstore is deployed.

Arguments:
    vectorstore (VectorstoreMeta): the vectorstore.
"""

vectorstore_destroyed = Signal()
"""
Sent when a vectorstore's database, and its data, is destroyed.

Arguments:
    vectorstore (VectorstoreMeta): the vectorstore.
"""

vectorstore_status_changed = Signal()
"""
Sent when a vectorstore's status changes.

Arguments:
    vectorstore (VectorstoreMeta): the vectorstore.
    previous (str): its previous status.
    status (str): its status, e.g. ready or failed.
    message (str): why, e.g. the error.
"""

document_loaded = Signal()
"""
Sent when a document's chunks are loaded into its vectorstore.

Arguments:
    document (VectorstoreDocument): the document.
"""

document_load_failed = Signal()
"""
Sent when a document cannot be loaded.

Arguments:
    document (VectorstoreDocument): the document.
    error (str): why.
"""
