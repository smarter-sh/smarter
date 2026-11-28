"""
A managed vector database's operations, executed by the tool runner: the ``vectorstore`` kind of tool call.

A managed vectorstore's database is a service at a host that its owner chooses: a Qdrant Cloud cluster at its
ApiConnection's url, or Pinecone. Connecting to it from the app or the worker, which hold every credential of the
platform's and reach its private network, would let a manifest point them at any address. So each operation is
resolved in the app, where the database and the Smarter Secrets are, into a :class:`VectorstoreToolCall`: the url, the
api key, the index's name, the operation and its parameters, with every vector already embedded. The tool runner
executes it with :func:`execute_vectorstore_call`, in the tool worker, which holds no credential of the platform's and
reaches no private address (ADR-038, issue #1081).

A self-hosted Qdrant server, which Smarter runs in the cluster, is reached in process, with the same operations
(:func:`run_vectorstore_operation` with a ``client``): the tool worker can't reach the cluster's private network, by
design. So is a client that a test injects.

The operations are plain functions of the vendor's client, in :data:`QDRANT_OPERATIONS` and
:data:`PINECONE_OPERATIONS`, so that both paths run the same code. Their parameters and results are JSON. Nothing here
reads the database.

.. warning::

    A resolved call holds the api key. It is excluded from ``repr()``. Never log the call's ``model_dump()``.
"""

from typing import Any, Callable, Final, Literal, Optional

from pinecone import Pinecone
from pinecone.db_control.models import ServerlessSpec
from pinecone.exceptions import (
    ForbiddenException,
    PineconeApiException,
    UnauthorizedException,
)
from pydantic import Field, JsonValue
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from smarter.apps.llmtool.plugin import safe_http
from smarter.apps.llmtool.runner import ToolCall, ToolCallResult, get_tool_runner
from smarter.lib.typing import SmarterDictType

from .backends.base import (
    VectorStoreBackendConnectionError,
    VectorStoreBackendCredentialsError,
    VectorStoreBackendError,
    VectorStoreBackendRejectedError,
)

VECTORSTORE_TOOL_CALL_KIND: Final = "vectorstore"
"""The ``kind`` of a managed vector database's operation, which selects :func:`execute_vectorstore_call`."""

QDRANT: Final = "qdrant"
PINECONE: Final = "pinecone"

DEFAULT_TIMEOUT_SECONDS = 30.0
"""How long an operation may take, unless it names its own."""

CREDENTIALS_STATUS = 401
"""The ``status_code`` of a failure because the database refused the api key."""

REJECTED_STATUS = 422
"""The ``status_code`` of a failure because the database refused the request, and would refuse it again."""

CONNECTION_STATUS = 503
"""The ``status_code`` of any other failure: the database couldn't be reached, or failed, which may pass."""

QDRANT_TIMEOUT = 30
QDRANT_DISTANCES = {
    "cosine": models.Distance.COSINE,
    "euclidean": models.Distance.EUCLID,
    "dotproduct": models.Distance.DOT,
}
QDRANT_CONTENT_KEY = "page_content"
"""Where a Qdrant point keeps its chunk's text, as LangChain's QdrantVectorStore stores it, so its collections stay readable."""

QDRANT_METADATA_KEY = "metadata"
"""Where a Qdrant point keeps its chunk's metadata, as LangChain's QdrantVectorStore stores it."""

QDRANT_DOCUMENT_ID_KEY = "metadata.document_id"
QDRANT_REFUSED_KEY_STATUSES = (401, 403)

PINECONE_TEXT_KEY = "text"
"""Where a Pinecone vector keeps its chunk's text, in its metadata, as LangChain's PineconeVectorStore stores it."""

PINECONE_DONT_WAIT = -1
"""The ``timeout`` that makes Pinecone's create_index and delete_index return at once, rather than wait."""

PINECONE_REJECTED_STATUSES = (400, 403, 422)
"""Pinecone's http statuses for a request that it would refuse again, e.g. an invalid dimension or a full quota."""


class VectorstoreToolCall(ToolCall):
    """
    A managed vector database's operation, resolved for execution.

    :ivar backend: ``qdrant`` or ``pinecone``.
    :ivar url: The Qdrant Cloud cluster's url, from the vectorstore's ApiConnection. Pinecone's is its own.
    :ivar api_key: The database's api key, from the ApiConnection's Secret.
    :ivar index_name: The collection's or the index's name.
    :ivar operation: The operation, a key of :data:`QDRANT_OPERATIONS` or :data:`PINECONE_OPERATIONS`.
    :ivar params: The operation's parameters, as JSON, e.g. the vectors to upsert, already embedded.
    :ivar timeout: Seconds that the operation may take.
    """

    kind: Literal["vectorstore"] = VECTORSTORE_TOOL_CALL_KIND
    backend: Literal["qdrant", "pinecone"]
    url: str = ""
    api_key: str = Field(default="", repr=False)
    index_name: str
    operation: str
    params: dict[str, JsonValue] = Field(default_factory=dict)
    timeout: float = DEFAULT_TIMEOUT_SECONDS


# --- Qdrant --------------------------------------------------------------------------------------------------------
def qdrant_filter(metadata_filter: Optional[SmarterDictType]) -> Optional[models.Filter]:
    """A Qdrant filter that matches chunks whose metadata has every value of metadata_filter."""
    if not metadata_filter:
        return None
    conditions: list[models.Condition] = []
    for key, value in metadata_filter.items():
        conditions.append(
            models.FieldCondition(key=f"{QDRANT_METADATA_KEY}.{key}", match=models.MatchValue(value=value))
        )
    return models.Filter(must=conditions)


def qdrant_exists(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Whether the collection exists."""
    exists = client.collection_exists(name)
    return bool(exists)


def qdrant_create(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Create the collection, with a payload index on each chunk's document id.

    ``params``: dimension, metric.
    """
    distance = QDRANT_DISTANCES[str(params["metric"])]
    vectors_config = models.VectorParams(size=int(params["dimension"]), distance=distance)
    client.create_collection(collection_name=name, vectors_config=vectors_config)
    # chunks are found by document when a document is deleted, or loaded again.
    client.create_payload_index(
        collection_name=name,
        field_name=QDRANT_DOCUMENT_ID_KEY,
        field_schema=models.PayloadSchemaType.INTEGER,
    )
    return None


def qdrant_drop(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Delete the collection, if it exists, and its data."""
    if client.collection_exists(name):
        client.delete_collection(name)
    return None


def qdrant_stats(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """The collection's exact vector count, status, segments count and indexed vectors count."""
    info = client.get_collection(name)
    count = client.count(name, exact=True).count
    stats: SmarterDictType = {
        "vector_count": count,
        "status": str(getattr(info.status, "value", info.status)),
        "segments_count": info.segments_count,
        "indexed_vectors_count": info.indexed_vectors_count,
    }
    return stats


def qdrant_upsert(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Insert, or replace, chunks.

    ``params``: ids, vectors, texts, metadatas, the same length.
    """
    points: list[models.PointStruct] = []
    for point_id, vector, text, metadata in zip(params["ids"], params["vectors"], params["texts"], params["metadatas"]):
        payload = {QDRANT_CONTENT_KEY: text, QDRANT_METADATA_KEY: metadata}
        points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))
    if points:
        client.upsert(collection_name=name, points=points)
    return None


def qdrant_delete(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Delete chunks by id.

    ``params``: ids. Ids that don't exist are ignored.
    """
    # PointIdsList.points is an invariant List[ExtendedPointId], which a list[str] does not match.
    points: list[models.ExtendedPointId] = list(params["ids"])
    if points:
        client.delete(name, points_selector=models.PointIdsList(points=points))
    return None


def qdrant_delete_document(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Delete every chunk of a document, whatever their number.

    ``params``: document_id.
    """
    condition = models.FieldCondition(key=QDRANT_DOCUMENT_ID_KEY, match=models.MatchValue(value=params["document_id"]))
    selector = models.FilterSelector(filter=models.Filter(must=[condition]))
    client.delete(name, points_selector=selector)
    return None


def qdrant_query(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """
    The chunks closest to a vector, best first.

    ``params``: vector, limit, and optionally filter (metadata values), score_threshold, and with_vectors.

    :returns: Each match's id, score, text, metadata, and vector if asked for.
    """
    response = client.query_points(
        collection_name=name,
        query=params["vector"],
        limit=int(params["limit"]),
        query_filter=qdrant_filter(params.get("filter")),
        score_threshold=params.get("score_threshold"),
        with_payload=True,
        with_vectors=bool(params.get("with_vectors")),
    )
    matches: list[JsonValue] = []
    for point in response.points:
        payload = dict(point.payload or {})
        match: SmarterDictType = {
            "id": str(point.id),
            "score": point.score,
            "text": payload.get(QDRANT_CONTENT_KEY, ""),
            "metadata": dict(payload.get(QDRANT_METADATA_KEY) or {}),
        }
        if params.get("with_vectors"):
            match["vector"] = point.vector
        matches.append(match)
    return matches


def qdrant_create_snapshot(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Take a snapshot of the collection, and wait for it.

    :returns: its name and size, or None.
    """
    description = client.create_snapshot(name, wait=True)
    if description is None:
        return None
    snapshot: SmarterDictType = {"name": description.name, "size_bytes": description.size}
    return snapshot


def qdrant_delete_snapshot(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Delete a snapshot of the collection, and wait for it.

    ``params``: name.
    """
    client.delete_snapshot(name, str(params["name"]), wait=True)
    return None


def qdrant_restore_snapshot(client: QdrantClient, name: str, params: SmarterDictType) -> JsonValue:
    """Recover the collection from a snapshot on the self-hosted server's volume.

    ``params``: location.
    """
    client.recover_snapshot(name, location=str(params["location"]), wait=True)
    return None


QDRANT_OPERATIONS: dict[str, Callable[[Any, str, SmarterDictType], JsonValue]] = {
    "exists": qdrant_exists,
    "create": qdrant_create,
    "drop": qdrant_drop,
    "stats": qdrant_stats,
    "upsert": qdrant_upsert,
    "delete": qdrant_delete,
    "delete_document": qdrant_delete_document,
    "query": qdrant_query,
    "create_snapshot": qdrant_create_snapshot,
    "delete_snapshot": qdrant_delete_snapshot,
    "restore_snapshot": qdrant_restore_snapshot,
}
"""Qdrant's operations, by name: each a function of a QdrantClient, the collection's name, and its parameters."""


def qdrant_error(operation: str, error: Exception) -> VectorStoreBackendError:
    """
    Return the backend error of an exception from Qdrant.

    :param operation: The operation that failed.
    :param error: Qdrant's exception.
    :returns: A credentials error for a refused api key, a connection error for anything else.
    """
    if isinstance(error, VectorStoreBackendError):
        return error
    if isinstance(error, UnexpectedResponse) and error.status_code in QDRANT_REFUSED_KEY_STATUSES:
        return VectorStoreBackendCredentialsError(f"Qdrant refused the api key: {error}")
    return VectorStoreBackendConnectionError(f"Qdrant could not {operation}: {error}")


# --- Pinecone ------------------------------------------------------------------------------------------------------
def pinecone_exists(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Whether the index exists."""
    exists = client.has_index(name)
    return bool(exists)


def pinecone_index_ready(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Whether the index, which exists, is ready: Pinecone takes a minute or two to initialize a new one."""
    status = client.describe_index(name).status
    if isinstance(status, dict):
        ready = status.get("ready")
    else:
        ready = getattr(status, "ready", True)
    return bool(ready)


def pinecone_create(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """
    Create a serverless index, without waiting for it.

    ``params``: cloud, region, dimension, metric, deletion_protection (``enabled`` or ``disabled``), tags.
    """
    spec = ServerlessSpec(cloud=str(params.get("cloud") or "aws"), region=str(params.get("region") or "us-east-1"))
    client.create_index(
        name=name,
        spec=spec,
        dimension=int(params["dimension"]),
        metric=str(params["metric"]),
        deletion_protection=str(params.get("deletion_protection") or "disabled"),
        tags=dict(params.get("tags") or {}),
        timeout=PINECONE_DONT_WAIT,
    )
    return None


def pinecone_drop(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Delete the index, if it exists, and its data, without waiting for it."""
    if client.has_index(name):
        client.delete_index(name, timeout=PINECONE_DONT_WAIT)
    return None


def pinecone_stats(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """The index's vector count, dimension and fullness."""
    response = client.Index(name=name).describe_index_stats()
    stats: SmarterDictType = response if isinstance(response, dict) else response.to_dict()
    retval: SmarterDictType = {
        "vector_count": stats.get("total_vector_count", 0),
        "dimension": stats.get("dimension"),
        "index_fullness": stats.get("index_fullness"),
    }
    return retval


def pinecone_upsert(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Insert, or replace, chunks, with each text in its metadata.

    ``params``: ids, vectors, texts, metadatas.
    """
    records = []
    for chunk_id, vector, text, metadata in zip(params["ids"], params["vectors"], params["texts"], params["metadatas"]):
        record_metadata = {**dict(metadata or {}), PINECONE_TEXT_KEY: text}
        records.append({"id": chunk_id, "values": vector, "metadata": record_metadata})
    if records:
        client.Index(name=name).upsert(vectors=records)
    return None


def pinecone_delete(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Delete chunks by id.

    ``params``: ids. Ids that don't exist are ignored.
    """
    ids = list(params["ids"])
    if ids:
        client.Index(name=name).delete(ids=ids)
    return None


def pinecone_query(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """
    The vectors closest to a vector, best first.

    ``params``: vector, limit, and optionally filter (a Pinecone metadata filter) and with_vectors.

    :returns: Each match's id, score, text and metadata, and vector if asked for. A match without text, e.g. a vector
        that something other than Smarter wrote, is left out.
    """
    with_vectors = bool(params.get("with_vectors"))
    response = client.Index(name=name).query(
        vector=params["vector"],
        top_k=int(params["limit"]),
        include_values=with_vectors,
        include_metadata=True,
        filter=params.get("filter"),
    )
    data = response.to_dict() if hasattr(response, "to_dict") else response
    matches: list[JsonValue] = []
    for raw in list(data.get("matches") or []):
        metadata = dict(raw.get("metadata") or {})
        if PINECONE_TEXT_KEY not in metadata:
            continue
        text = metadata.pop(PINECONE_TEXT_KEY)
        match: SmarterDictType = {"id": raw.get("id"), "score": raw.get("score"), "text": text, "metadata": metadata}
        if with_vectors:
            match["vector"] = raw.get("values")
        matches.append(match)
    return matches


def pinecone_create_backup(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Back the index up.

    ``params``: name, description. :returns: the backup's id, size, and status.
    """
    backup = client.create_backup(
        index_name=name, backup_name=str(params["name"]), description=str(params["description"])
    )
    data = backup.to_dict() if hasattr(backup, "to_dict") else {}
    snapshot: SmarterDictType = {
        "name": data.get("backup_id") or params["name"],
        "size_bytes": data.get("size_bytes"),
        "status": str(data.get("status", "Ready")),
    }
    return snapshot


def pinecone_delete_backup(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """Delete a backup.

    ``params``: name, the backup's id.
    """
    client.delete_backup(backup_id=str(params["name"]))
    return None


def pinecone_restore_backup(client: Pinecone, name: str, params: SmarterDictType) -> JsonValue:
    """
    Replace the index with a new one from a backup.

    ``params``: name, the backup's id; deletion_protection.

    Pinecone requires that the index is deleted first, so this waits until it is.
    """
    if client.has_index(name):
        client.delete_index(name)
    client.create_index_from_backup(
        name=name,
        backup_id=str(params["name"]),
        deletion_protection=str(params.get("deletion_protection") or "disabled"),
    )
    return None


PINECONE_OPERATIONS: dict[str, Callable[[Any, str, SmarterDictType], JsonValue]] = {
    "exists": pinecone_exists,
    "index_ready": pinecone_index_ready,
    "create": pinecone_create,
    "drop": pinecone_drop,
    "stats": pinecone_stats,
    "upsert": pinecone_upsert,
    "delete": pinecone_delete,
    "query": pinecone_query,
    "create_snapshot": pinecone_create_backup,
    "delete_snapshot": pinecone_delete_backup,
    "restore_snapshot": pinecone_restore_backup,
}
"""Pinecone's operations, by name: each a function of a Pinecone client, the index's name, and its parameters."""


def pinecone_error(operation: str, error: Exception) -> VectorStoreBackendError:
    """
    Return the backend error of an exception from Pinecone, by whether retrying could help.

    :param operation: The operation that failed.
    :param error: Pinecone's exception.
    :returns: A credentials error for a refused api key, a rejected error for another request that Pinecone would
        refuse again, and a connection error for anything else, e.g. a timeout or a 5xx, which may pass.
    """
    if isinstance(error, VectorStoreBackendError):
        return error
    message = f"Pinecone could not {operation}: {error}"
    if isinstance(error, UnauthorizedException):
        return VectorStoreBackendCredentialsError(f"Pinecone refused the api key: {error}")
    if isinstance(error, ForbiddenException):
        return VectorStoreBackendRejectedError(message)
    if isinstance(error, PineconeApiException) and error.status_code in PINECONE_REJECTED_STATUSES:
        return VectorStoreBackendRejectedError(message)
    return VectorStoreBackendConnectionError(message)


# --- running an operation ------------------------------------------------------------------------------------------
OPERATIONS = {QDRANT: QDRANT_OPERATIONS, PINECONE: PINECONE_OPERATIONS}
ERRORS = {QDRANT: qdrant_error, PINECONE: pinecone_error}


def run_in_process(backend: str, client: Any, index_name: str, operation: str, params: SmarterDictType) -> JsonValue:
    """
    Run an operation on a client in this process, and raise its errors as backend errors.

    :param backend: ``qdrant`` or ``pinecone``.
    :param client: The vendor's client.
    :param index_name: The collection's or the index's name.
    :param operation: The operation's name.
    :param params: Its parameters.
    :returns: The operation's result.
    :raises VectorStoreBackendError: If the operation is unknown, or fails, classified as the vendor's error says.
    """
    function = OPERATIONS[backend].get(operation)
    if function is None:
        raise VectorStoreBackendError(f"{backend} has no operation {operation!r}.")
    try:
        value = function(client, index_name, params)
    except Exception as e:  # pylint: disable=broad-exception-caught
        raise ERRORS[backend](operation, e) from e
    return value


def status_of(error: VectorStoreBackendError) -> int:
    """The ``status_code`` that carries a backend error's class back from the tool worker."""
    if isinstance(error, VectorStoreBackendCredentialsError):
        return CREDENTIALS_STATUS
    if isinstance(error, VectorStoreBackendRejectedError):
        return REJECTED_STATUS
    return CONNECTION_STATUS


def error_of(status_code: Optional[int], message: str) -> VectorStoreBackendError:
    """The backend error of a failure from the tool worker, by its ``status_code`` (:func:`status_of`)."""
    if status_code == CREDENTIALS_STATUS:
        return VectorStoreBackendCredentialsError(message)
    if status_code == REJECTED_STATUS:
        return VectorStoreBackendRejectedError(message)
    return VectorStoreBackendConnectionError(message)


def client_for(call: VectorstoreToolCall) -> Any:
    """
    Return the vendor's client of a call, connected to nothing yet.

    A Qdrant Cloud url must resolve to public addresses only, on any port: the managed database is the vectorstore
    owner's choice, and must not be the platform's own network.

    :raises VectorStoreBackendError: If the url is not permitted, or there is no api key.
    """
    if call.backend == PINECONE:
        if not call.api_key:
            raise VectorStoreBackendCredentialsError("There is no Pinecone API key.")
        return Pinecone(api_key=call.api_key)
    try:
        safe_http.validate_destination_url(call.url, require_https=False)
    except safe_http.SafeHttpError as e:
        raise VectorStoreBackendRejectedError(f"The Qdrant Cloud url is not permitted: {e}") from e
    return QdrantClient(url=call.url, api_key=call.api_key or None, timeout=QDRANT_TIMEOUT)


def execute_vectorstore_call(call: ToolCall) -> ToolCallResult:
    """
    Execute a resolved operation of a managed vector database.

    :param call: The call, a :class:`VectorstoreToolCall`.
    :returns: The operation's result, as JSON; or a result with a ``failure``, whose ``status_code`` says whether the
        api key was refused (401), the request would be refused again (422), or the database couldn't be reached (503).
    :raises TypeError: If the call isn't a :class:`VectorstoreToolCall`.
    """
    if not isinstance(call, VectorstoreToolCall):
        raise TypeError(f"execute_vectorstore_call() needs a VectorstoreToolCall, not a {type(call).__name__}.")
    try:
        client = client_for(call)
        value = run_in_process(call.backend, client, call.index_name, call.operation, call.params)
    except VectorStoreBackendError as e:
        return ToolCallResult(failure=str(e), status_code=status_of(e))
    result = ToolCallResult(value=value)
    return result


# pylint: disable=too-many-arguments
def run_vectorstore_operation(
    backend: str,
    operation: str,
    params: Optional[SmarterDictType] = None,
    *,
    index_name: str,
    client: Any = None,
    url: str = "",
    api_key: str = "",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> JsonValue:
    """
    Run a vector database's operation: in process on a client, or through the tool runner for a managed database.

    :param backend: ``qdrant`` or ``pinecone``.
    :param operation: The operation's name.
    :param params: Its parameters, as JSON.
    :param index_name: The collection's or the index's name.
    :param client: A client to run it on, in this process: a self-hosted Qdrant server's, or one that a test injects.
        None sends the call, with ``url`` and ``api_key``, to the tool runner.
    :param url: The managed Qdrant Cloud cluster's url.
    :param api_key: The managed database's api key.
    :param timeout: Seconds that the operation may take.
    :returns: The operation's result.
    :raises VectorStoreBackendError: If the operation fails, classified as credentials, rejected or connection.
    """
    params = params or {}
    if client is not None:
        return run_in_process(backend, client, index_name, operation, params)
    call = VectorstoreToolCall(
        backend=backend,  # type: ignore[arg-type]
        url=url,
        api_key=api_key,
        index_name=index_name,
        operation=operation,
        params=params,
        timeout=timeout,
    )
    result = get_tool_runner().run(call)
    if result.failure is not None:
        raise error_of(result.status_code, result.failure)
    return result.value


__all__ = [
    "PINECONE",
    "PINECONE_OPERATIONS",
    "QDRANT",
    "QDRANT_OPERATIONS",
    "VECTORSTORE_TOOL_CALL_KIND",
    "VectorstoreToolCall",
    "error_of",
    "execute_vectorstore_call",
    "pinecone_error",
    "qdrant_error",
    "qdrant_filter",
    "run_in_process",
    "run_vectorstore_operation",
    "status_of",
]
