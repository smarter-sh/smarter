# pylint: disable=W0613
"""
Vectorstore api/v1/vectorstores views.

Vectorstores are created and updated by applying manifests, with ``smarter apply``. These views
load and search them, and maintain them:

- ``GET vectorstores/``: the vectorstores that the user may read.
- ``GET vectorstores/<hashed_id>/``: a vectorstore that the user may read.
- ``GET vectorstores/<hashed_id>/status/``: check its status and statistics, now.
- ``POST vectorstores/<hashed_id>/deploy/`` and ``POST vectorstores/<hashed_id>/undeploy/``.
- ``GET vectorstores/<hashed_id>/documents/``: its documents.
- ``POST vectorstores/<hashed_id>/documents/``: add documents, and queue them to be loaded: files,
  as multipart/form-data, or JSON ``{"name": ..., "text": ...}`` or ``{"url": ...}``.
- ``DELETE vectorstores/<hashed_id>/documents/<document_id>/``: remove a document, and its chunks.
- ``POST vectorstores/<hashed_id>/search/``: ``{"query": ..., "k": 4, "searchType": "similarity",
  "scoreThreshold": null, "fetchK": null, "lambdaMult": null, "filter": {}}``.
- ``GET vectorstores/<hashed_id>/snapshots/``: its snapshots, or backups.
- ``POST vectorstores/<hashed_id>/snapshots/``: take one now.
- ``POST vectorstores/<hashed_id>/snapshots/<snapshot_id>/restore/``: restore one.

Reading and searching require read permission. Everything else requires ownership.
"""

from http import HTTPStatus
from typing import Any

from django.db.models import QuerySet
from django.http import Http404, JsonResponse
from rest_framework.request import Request

from smarter.apps.plugin.plugin.safe_http import SafeHttpError, fetch
from smarter.apps.vectorstore.caching import (
    invalidate_all_cached_vectorstores_for_user_profile,
)
from smarter.apps.vectorstore.extract import (
    MAX_DOCUMENT_BYTES,
    VectorstoreExtractionError,
)
from smarter.apps.vectorstore.models import (
    VectorstoreDocument,
    VectorstoreDocumentSource,
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreSnapshot,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.serializers import (
    VectorstoreDocumentSerializer,
    VectorstoreSerializer,
    VectorstoreSnapshotSerializer,
)
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.exceptions import SmarterException
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])

MAX_SEARCH_RESULTS = 50


def error(message: str, status: int = HTTPStatus.BAD_REQUEST) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


class VectorstoreViewBase(SmarterAuthenticatedAPIView):
    """
    Base class of the views of one vectorstore, identified by ``hashed_id`` or ``vectorstore_id``.

    :meth:`get_vectorstore` returns it only if the user may read it, or, with ``owner=True``,
    owns it. Otherwise it raises Http404, so that other accounts' vectorstores are not disclosed.
    """

    service_class = VectorstoreService

    def get_vectorstore(self, request: Request, owner: bool = False, **kwargs) -> VectorstoreMeta:
        hashed_id = kwargs.get("hashed_id")
        vectorstore_id = VectorstoreMeta.id_from_hashed_id(hashed_id) if hashed_id else kwargs.get("vectorstore_id")
        if not vectorstore_id:
            raise Http404("Vectorstore not found")
        queryset = (
            VectorstoreMeta.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
            if owner
            else VectorstoreMeta.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        )
        vectorstore = (
            queryset.select_related("user_profile__user", "user_profile__account").filter(pk=vectorstore_id).first()
        )
        if vectorstore is None:
            raise Http404("Vectorstore not found")
        return vectorstore

    def get_service(self, vectorstore: VectorstoreMeta) -> VectorstoreService:
        return self.service_class(vectorstore)


class VectorstoreListView(SmarterAuthenticatedListAPIView):
    """The vectorstores that the user may read."""

    serializer_class = VectorstoreSerializer

    def get_queryset(self, *args, **kwargs) -> QuerySet[VectorstoreMeta]:
        return VectorstoreMeta.objects.with_read_permission_for(user=self.request.user).order_by("name")  # type: ignore[attr-defined]


class VectorstoreView(VectorstoreViewBase):
    """A vectorstore that the user may read."""

    serializer_class = VectorstoreSerializer

    def get(self, request: Request, *args, **kwargs):
        return JsonResponse(VectorstoreSerializer(self.get_vectorstore(request, **kwargs)).data)


class VectorstoreStatusView(VectorstoreViewBase):
    """Check a vectorstore's status and statistics, now."""

    def get(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, **kwargs)
        status = self.get_service(vectorstore).reconcile()
        return JsonResponse(
            {
                "vectorstore": vectorstore.name,
                "status": status,
                "message": vectorstore.status_message,
                "vectorCount": vectorstore.vector_count,
                "stats": vectorstore.stats,
            }
        )


class VectorstoreDeployView(VectorstoreViewBase):
    """Create the database of a vectorstore that the user owns."""

    def post(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        try:
            self.get_service(vectorstore).deploy()
        except SmarterException as e:
            return error(str(e))
        vectorstore.refresh_from_db()
        invalidate_all_cached_vectorstores_for_user_profile(vectorstore.user_profile)
        return JsonResponse(VectorstoreSerializer(vectorstore).data, status=HTTPStatus.ACCEPTED)


class VectorstoreUndeployView(VectorstoreViewBase):
    """Stop serving a vectorstore that the user owns.

    A self-hosted server's data is kept.
    """

    def post(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        try:
            self.get_service(vectorstore).undeploy()
        except SmarterException as e:
            return error(str(e))
        vectorstore.refresh_from_db()
        invalidate_all_cached_vectorstores_for_user_profile(vectorstore.user_profile)
        return JsonResponse(VectorstoreSerializer(vectorstore).data)


class VectorstoreDocumentsView(VectorstoreViewBase):
    """List a vectorstore's documents, or add documents to one that the user owns."""

    def get(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, **kwargs)
        documents = vectorstore.documents.order_by("-created_at")  # type: ignore[attr-defined]
        return JsonResponse({"documents": VectorstoreDocumentSerializer(documents, many=True).data})

    def post(self, request: Request, *args, **kwargs):  # pylint: disable=too-many-locals
        """
        Add documents, and queue them to be loaded.

        Files, as multipart/form-data, are read, and their text extracted, now. The files
        themselves are not kept. Optional ``metadata``, a JSON object, is stored with each chunk.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.vectorstore.tasks import load_vectorstore_document

        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        service = self.get_service(vectorstore)
        metadata = request.data.get("metadata") if hasattr(request.data, "get") else None
        if metadata is not None and not isinstance(metadata, dict):
            return error("metadata must be a JSON object.")
        added: list[VectorstoreDocument] = []
        existing: list[VectorstoreDocument] = []
        try:
            for name, data, text, content_type, source in self.sources(request):
                document, created = service.add_document(
                    name=name, data=data, text=text, content_type=content_type, source=source, metadata=metadata
                )
                (added if created else existing).append(document)
        except (VectorstoreExtractionError, SafeHttpError, ValueError) as e:
            return error(str(e))
        if not added and not existing:
            return error("Provide files, as multipart/form-data, or JSON with text or url.")
        queued = vectorstore.status == VectorstoreStatus.READY
        if queued:
            for document in added:
                load_vectorstore_document.delay(document.pk)
        return JsonResponse(
            {
                "documents": VectorstoreDocumentSerializer(added, many=True).data,
                "duplicates": VectorstoreDocumentSerializer(existing, many=True).data,
                "queued": queued,
                "message": (
                    "" if queued else "The vectorstore is not ready. Its documents are loaded once it is deployed."
                ),
            },
            status=HTTPStatus.ACCEPTED,
        )

    @staticmethod
    def sources(request: Request):
        """The documents of a request: uploaded files, text, or a URL."""
        for upload in request.FILES.getlist("files") or request.FILES.getlist("file"):
            if upload.size > MAX_DOCUMENT_BYTES:
                raise ValueError(f"{upload.name} is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MiB.")
            yield upload.name, upload.read(), None, upload.content_type, VectorstoreDocumentSource.UPLOAD
        data: Any = request.data if hasattr(request.data, "get") else {}
        if data.get("text"):
            yield data.get("name") or "text", None, str(data["text"]), "text/plain", VectorstoreDocumentSource.TEXT
        if data.get("url"):
            response = fetch(str(data["url"]), max_bytes=MAX_DOCUMENT_BYTES)
            yield response.url, response.content, None, response.content_type, VectorstoreDocumentSource.URL


class VectorstoreDocumentView(VectorstoreViewBase):
    """Remove a document, and its chunks, from a vectorstore that the user owns."""

    def delete(self, request: Request, *args, **kwargs):
        # pylint: disable=import-outside-toplevel
        from smarter.apps.vectorstore.tasks import delete_vectorstore_document

        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        document = vectorstore.documents.filter(pk=kwargs.get("document_id")).first()  # type: ignore[attr-defined]
        if document is None:
            raise Http404("Document not found")
        document.status = VectorstoreDocumentStatus.DELETING
        document.save(update_fields=["status", "updated_at"])
        delete_vectorstore_document.delay(document.pk)
        return JsonResponse({"document": document.name, "status": document.status}, status=HTTPStatus.ACCEPTED)


class VectorstoreSearchView(VectorstoreViewBase):
    """Search a vectorstore that the user may read."""

    def post(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, **kwargs)
        data: Any = request.data if hasattr(request.data, "get") else {}
        try:
            k = min(int(data.get("k", 4)), MAX_SEARCH_RESULTS)
            results = self.get_service(vectorstore).search(
                query=str(data.get("query") or ""),
                k=k,
                search_type=data.get("searchType", "similarity"),
                score_threshold=data.get("scoreThreshold"),
                fetch_k=data.get("fetchK"),
                lambda_mult=data.get("lambdaMult"),
                metadata_filter=data.get("filter") or None,
            )
        except (SmarterException, ValueError, TypeError) as e:
            return error(str(e))
        return JsonResponse(
            {
                "vectorstore": vectorstore.name,
                "results": [{"id": r.id, "text": r.text, "metadata": r.metadata, "score": r.score} for r in results],
            }
        )


class VectorstoreSnapshotsView(VectorstoreViewBase):
    """List a vectorstore's snapshots, or take one now."""

    def get(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, **kwargs)
        return JsonResponse(
            {"snapshots": VectorstoreSnapshotSerializer(vectorstore.snapshots.all(), many=True).data}  # type: ignore[attr-defined]
        )

    def post(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        try:
            snapshot = self.get_service(vectorstore).snapshot(scheduled=False)
        except SmarterException as e:
            return error(str(e))
        return JsonResponse(VectorstoreSnapshotSerializer(snapshot).data, status=HTTPStatus.CREATED)


class VectorstoreRestoreView(VectorstoreViewBase):
    """Replace a vectorstore's data with one of its snapshots."""

    def post(self, request: Request, *args, **kwargs):
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        snapshot = VectorstoreSnapshot.objects.filter(vectorstore=vectorstore, pk=kwargs.get("snapshot_id")).first()
        if snapshot is None:
            raise Http404("Snapshot not found")
        try:
            self.get_service(vectorstore).restore(snapshot)
        except SmarterException as e:
            return error(str(e))
        return JsonResponse(
            {"vectorstore": vectorstore.name, "restored": snapshot.name, "vectorCount": vectorstore.vector_count}
        )
