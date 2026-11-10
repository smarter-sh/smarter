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

The responses are built from the models of :mod:`smarter.apps.vectorstore.contract.models`, which the
Smarter api's OpenAPI document publishes. Errors are Django REST framework's ``{"detail": ...}``.
"""

from collections.abc import Mapping
from http import HTTPStatus

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, fetch
from smarter.apps.vectorstore.caching import (
    invalidate_all_cached_vectorstores_for_user_profile,
)
from smarter.apps.vectorstore.contract.models import (
    VectorstoreApiDocument,
    VectorstoreApiDocumentDeleted,
    VectorstoreApiDocuments,
    VectorstoreApiDocumentsAdded,
    VectorstoreApiRestored,
    VectorstoreApiSearchResult,
    VectorstoreApiSearchResults,
    VectorstoreApiSnapshot,
    VectorstoreApiSnapshots,
    VectorstoreApiStatus,
    VectorstoreApiVectorstore,
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
from smarter.apps.vectorstore.serializers import VectorstoreSerializer
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.exceptions import SmarterException
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING])

MAX_SEARCH_RESULTS = 50


def error(message: str, status: int = HTTPStatus.BAD_REQUEST) -> Response:
    """
    An error response: Django REST framework's ``{"detail": ...}``, as every error of the REST api.

    :param message: The error's message.
    :param status: The HTTP status. By default 400 Bad Request.
    :returns: The response.
    """
    return Response({"detail": message}, status=status)


class VectorstoreViewBase(SmarterAuthenticatedAPIView):
    """
    Base class of the views of one vectorstore, identified by ``hashed_id`` or ``vectorstore_id``.

    :meth:`get_vectorstore` returns it only if the user may read it, or, with ``owner=True``,
    owns it. Otherwise it raises Http404, so that other accounts' vectorstores are not disclosed.
    """

    service_class = VectorstoreService

    def get_vectorstore(self, request: Request, owner: bool = False, **kwargs) -> VectorstoreMeta:
        """
        Return the vectorstore of the url, if the user may read it, or, with ``owner``, owns it.

        :param request: The request, whose user's permissions are checked.
        :param owner: Require that the user owns it, rather than only may read it.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The vectorstore.
        :raises Http404: If it does not exist, or the user may not read, or own, it.
        """
        hashed_id = kwargs.get("hashed_id")
        if hashed_id:
            vectorstore_id = VectorstoreMeta.id_from_hashed_id(hashed_id)
        else:
            vectorstore_id = kwargs.get("vectorstore_id")
        if not vectorstore_id:
            raise Http404("Vectorstore not found")
        if owner:
            queryset = VectorstoreMeta.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
        else:
            queryset = VectorstoreMeta.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        queryset = queryset.select_related("user_profile__user", "user_profile__account")
        vectorstore = queryset.filter(pk=vectorstore_id).first()
        if vectorstore is None:
            raise Http404("Vectorstore not found")
        return vectorstore

    def get_service(self, vectorstore: VectorstoreMeta) -> VectorstoreService:
        """
        Return the service that operates a vectorstore, an instance of :attr:`service_class`.

        :param vectorstore: The vectorstore.
        :returns: Its service.
        """
        return self.service_class(vectorstore)


class VectorstoreListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The vectorstores that the user may read."""

    serializer_class = VectorstoreSerializer
    contract_model = VectorstoreApiVectorstore

    def item(self, row):
        """A vectorstore of the response, whose ``canDelete`` is the requesting user's."""
        return VectorstoreApiVectorstore.from_model(row, self.request.user).model_dump(mode="json")

    def get_queryset(self, *args, **kwargs) -> QuerySet[VectorstoreMeta]:
        """Return the vectorstores that the user may read, by name."""
        return VectorstoreMeta.objects.with_read_permission_for(user=self.request.user).order_by("name")  # type: ignore[attr-defined]


class VectorstoreView(VectorstoreViewBase):
    """A vectorstore that the user may read."""

    serializer_class = VectorstoreSerializer

    def get(self, request: Request, *args, **kwargs):
        """
        Return the vectorstore, with ``canDelete`` for the requesting user.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The vectorstore.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        vectorstore = self.get_vectorstore(request, **kwargs)
        return Response(VectorstoreApiVectorstore.from_model(vectorstore, request.user).model_dump(mode="json"))


class VectorstoreStatusView(VectorstoreViewBase):
    """Check a vectorstore's status and statistics, now."""

    def get(self, request: Request, *args, **kwargs):
        """
        Reconcile the vectorstore's status with its database, now, and return it with its statistics.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The status, message, vector count and statistics.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        vectorstore = self.get_vectorstore(request, **kwargs)
        status = self.get_service(vectorstore).reconcile()
        response = VectorstoreApiStatus(
            vectorstore=vectorstore.name,
            status=status,  # type: ignore[arg-type]
            message=vectorstore.status_message,
            vector_count=vectorstore.vector_count,
            stats=vectorstore.stats,
        )
        return Response(response.model_dump(mode="json"))


class VectorstoreDeployView(VectorstoreViewBase):
    """Create the database of a vectorstore that the user owns."""

    def post(self, request: Request, *args, **kwargs):
        """
        Deploy the vectorstore: create its database, and, if self-hosted, its server.

        Invalidates the owner's cached vectorstores.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The vectorstore, 202 Accepted, or 400 Bad Request if it could not be deployed.
        :raises Http404: If it does not exist, or the user does not own it.
        """
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        try:
            self.get_service(vectorstore).deploy()
        except SmarterException as e:
            return error(str(e))
        vectorstore.refresh_from_db()
        invalidate_all_cached_vectorstores_for_user_profile(vectorstore.user_profile)
        return Response(
            VectorstoreApiVectorstore.from_model(vectorstore, request.user).model_dump(mode="json"),
            status=HTTPStatus.ACCEPTED,
        )


class VectorstoreUndeployView(VectorstoreViewBase):
    """Stop serving a vectorstore that the user owns.

    A self-hosted server's data is kept.
    """

    def post(self, request: Request, *args, **kwargs):
        """
        Undeploy the vectorstore: stop serving it, and keep its data.

        Invalidates the owner's cached vectorstores.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The vectorstore, or 400 Bad Request if it could not be undeployed.
        :raises Http404: If it does not exist, or the user does not own it.
        """
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        try:
            self.get_service(vectorstore).undeploy()
        except SmarterException as e:
            return error(str(e))
        vectorstore.refresh_from_db()
        invalidate_all_cached_vectorstores_for_user_profile(vectorstore.user_profile)
        return Response(VectorstoreApiVectorstore.from_model(vectorstore, request.user).model_dump(mode="json"))


class VectorstoreDocumentsView(VectorstoreViewBase):
    """List a vectorstore's documents, or add documents to one that the user owns."""

    def get(self, request: Request, *args, **kwargs):
        """
        Return the vectorstore's documents, newest first.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The documents.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        vectorstore = self.get_vectorstore(request, **kwargs)
        documents = vectorstore.documents.order_by("-created_at")  # type: ignore[attr-defined]
        response = VectorstoreApiDocuments(documents=[VectorstoreApiDocument.from_model(row) for row in documents])
        return Response(response.model_dump(mode="json"))

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
        data = request.data
        metadata = None
        if isinstance(data, Mapping):
            metadata = data.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            return error("metadata must be a JSON object.")
        added: list[VectorstoreDocument] = []
        existing: list[VectorstoreDocument] = []
        try:
            for name, data, text, content_type, source in self.sources(request):
                document, created = service.add_document(
                    name=name, data=data, text=text, content_type=content_type, source=source, metadata=metadata
                )
                if created:
                    added.append(document)
                else:
                    existing.append(document)
        except (VectorstoreExtractionError, SafeHttpError, ValueError) as e:
            return error(str(e))
        if not added and not existing:
            return error("Provide files, as multipart/form-data, or JSON with text or url.")
        queued = vectorstore.status == VectorstoreStatus.READY
        if queued:
            for document in added:
                load_vectorstore_document.delay(document.pk)
        response = VectorstoreApiDocumentsAdded(
            documents=[VectorstoreApiDocument.from_model(row) for row in added],
            duplicates=[VectorstoreApiDocument.from_model(row) for row in existing],
            queued=queued,
            message="" if queued else "The vectorstore is not ready. Its documents are loaded once it is deployed.",
        )
        return Response(response.model_dump(mode="json"), status=HTTPStatus.ACCEPTED)

    @staticmethod
    def sources(request: Request):
        """The documents of a request: uploaded files, text, or a URL."""
        for upload in request.FILES.getlist("files") or request.FILES.getlist("file"):
            if upload.size > MAX_DOCUMENT_BYTES:
                raise ValueError(f"{upload.name} is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MiB.")
            yield upload.name, upload.read(), None, upload.content_type, VectorstoreDocumentSource.UPLOAD
        data: SmarterDictType = request.data if isinstance(request.data, dict) else {}
        if data.get("text"):
            yield data.get("name") or "text", None, str(data["text"]), "text/plain", VectorstoreDocumentSource.TEXT
        if data.get("url"):
            response = fetch(str(data["url"]), max_bytes=MAX_DOCUMENT_BYTES)
            yield response.url, response.content, None, response.content_type, VectorstoreDocumentSource.URL


class VectorstoreDocumentView(VectorstoreViewBase):
    """Remove a document, and its chunks, from a vectorstore that the user owns."""

    def delete(self, request: Request, *args, **kwargs):
        """
        Mark a document Deleting, and queue the Celery task that removes it and its chunks.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``, and ``document_id``.
        :returns: The document's name and status, 202 Accepted.
        :raises Http404: If the vectorstore or the document does not exist, or the user does not own it.
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.vectorstore.tasks import delete_vectorstore_document

        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        document_id = kwargs.get("document_id")
        if document_id is None:
            raise Http404("Document not found")
        document = vectorstore.documents.filter(pk=document_id).first()  # type: ignore[attr-defined]
        if document is None:
            raise Http404("Document not found")
        document.status = VectorstoreDocumentStatus.DELETING
        document.save(update_fields=["status", "updated_at"])
        delete_vectorstore_document.delay(document.pk)
        response = VectorstoreApiDocumentDeleted(document=document.name, status=document.status)  # type: ignore[arg-type]
        return Response(response.model_dump(mode="json"), status=HTTPStatus.ACCEPTED)


class VectorstoreSearchView(VectorstoreViewBase):
    """Search a vectorstore that the user may read."""

    def post(self, request: Request, *args, **kwargs):
        """
        Search the vectorstore with the JSON body's ``query``.

        The body may also have ``k``, at most :data:`MAX_SEARCH_RESULTS`, ``searchType``,
        ``scoreThreshold``, ``fetchK``, ``lambdaMult`` and ``filter``.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The results, or 400 Bad Request if the search failed.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        vectorstore = self.get_vectorstore(request, **kwargs)
        data: SmarterDictType = request.data if isinstance(request.data, dict) else {}
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
        response = VectorstoreApiSearchResults(
            vectorstore=vectorstore.name, results=[VectorstoreApiSearchResult.from_result(result) for result in results]
        )
        return Response(response.model_dump(mode="json"))


class VectorstoreSnapshotsView(VectorstoreViewBase):
    """List a vectorstore's snapshots, or take one now."""

    def get(self, request: Request, *args, **kwargs):
        """
        Return the vectorstore's snapshots.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The snapshots.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        vectorstore = self.get_vectorstore(request, **kwargs)
        snapshots = vectorstore.snapshots.all()  # type: ignore[attr-defined]
        response = VectorstoreApiSnapshots(snapshots=[VectorstoreApiSnapshot.from_model(row) for row in snapshots])
        return Response(response.model_dump(mode="json"))

    def post(self, request: Request, *args, **kwargs):
        """
        Take a snapshot of the vectorstore now.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``.
        :returns: The snapshot, 201 Created, or 400 Bad Request if it could not be taken.
        :raises Http404: If it does not exist, or the user does not own it.
        """
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        try:
            snapshot = self.get_service(vectorstore).snapshot(scheduled=False)
        except SmarterException as e:
            return error(str(e))
        return Response(VectorstoreApiSnapshot.from_model(snapshot).model_dump(mode="json"), status=HTTPStatus.CREATED)


class VectorstoreRestoreView(VectorstoreViewBase):
    """Replace a vectorstore's data with one of its snapshots."""

    def post(self, request: Request, *args, **kwargs):
        """
        Replace the vectorstore's data with the snapshot of the url.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorstore_id``, and ``snapshot_id``.
        :returns: The vectorstore, the snapshot and the vector count, or 400 Bad Request if it could not be restored.
        :raises Http404: If the vectorstore or the snapshot does not exist, or the user does not own it.
        """
        vectorstore = self.get_vectorstore(request, owner=True, **kwargs)
        snapshot_id = kwargs.get("snapshot_id")
        if snapshot_id is None:
            raise Http404("Snapshot not found")
        snapshot = VectorstoreSnapshot.objects.filter(vectorstore=vectorstore, pk=snapshot_id).first()
        if snapshot is None:
            raise Http404("Snapshot not found")
        try:
            self.get_service(vectorstore).restore(snapshot)
        except SmarterException as e:
            return error(str(e))
        response = VectorstoreApiRestored(
            vectorstore=vectorstore.name, restored=snapshot.name, vector_count=vectorstore.vector_count
        )
        return Response(response.model_dump(mode="json"))
