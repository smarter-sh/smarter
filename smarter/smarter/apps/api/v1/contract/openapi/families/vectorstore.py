"""The vectorstores' REST reads, search, documents and maintenance, under ``/api/v1/vectorstores/``."""

from smarter.apps.api.v1.contract.models import (
    OpenApiMediaType,
    OpenApiPathItem,
    OpenApiRequestBody,
    OpenApiSchema,
)
from smarter.apps.api.v1.contract.openapi.builders import (
    READ_PERMISSION,
    ApiFamily,
    id_or_hashed_id,
    integer_id,
    ref,
    rest_operation,
    rest_read,
)
from smarter.apps.vectorstore.const import namespace
from smarter.apps.vectorstore.contract.models import (
    VectorstoreApiAddText,
    VectorstoreApiDocumentDeleted,
    VectorstoreApiDocuments,
    VectorstoreApiDocumentsAdded,
    VectorstoreApiRestored,
    VectorstoreApiSearch,
    VectorstoreApiSearchResults,
    VectorstoreApiSnapshot,
    VectorstoreApiSnapshots,
    VectorstoreApiStatus,
    VectorstoreApiVectorstore,
)

VECTORSTORES = ApiFamily(
    name=namespace,
    resource=namespace,
    urlconf="smarter.apps.vectorstore.api.v1.urls",
    description="The {plural}' REST reads, search, documents and maintenance. Served only when the platform "
    "enables {plural} (SMARTER_ENABLE_VECTORSTORE).",
)
"""The vectorstores' family.

Its resource is its app's name: the descriptions write it in lowercase.
"""


def vectorstore_paths() -> dict[str, OpenApiPathItem]:
    """
    The vectorstores' REST reads and maintenance, relative to the server's ``/api/v1``.

    Reading and searching need read permission. Everything else needs ownership.

    :returns: The paths, e.g. ``{"/vectorstores/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = VECTORSTORES
    resource = family.resource
    vectorstore_id = id_or_hashed_id(resource)
    tag = family.tag
    owner = f"Only the {resource}'s owner may call it."
    files: OpenApiSchema = {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"type": "string", "contentMediaType": "application/octet-stream"},
                "description": "The files, e.g. PDFs and Word documents, of at most 50 MiB each.",
            },
            "metadata": {"type": "string", "description": "Metadata to store with each chunk, as a JSON object."},
        },
        "required": ["files"],
    }
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user may read, by name.",
                tag,
                VectorstoreApiVectorstore.__name__,
                many=True,
                parameters=[],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized} that the user may read.",
                tag,
                VectorstoreApiVectorstore.__name__,
                many=False,
                parameters=[vectorstore_id],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/status/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("status"),
                f"{family.a_capitalized}'s status",
                f"Check {family.a}'s status and statistics now, with its database.",
                tag,
                VectorstoreApiStatus.__name__,
                many=False,
                parameters=[vectorstore_id],
                note=READ_PERMISSION,
            )
        ),
        family.path("{id}/deploy/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("deploy"),
                f"Deploy {family.a}",
                f"Create the {resource}'s database: a Qdrant server on the platform's Kubernetes cluster, or a "
                f"Pinecone index. It creates billable infrastructure, and returns before it is ready. {owner}",
                tag,
                VectorstoreApiVectorstore.__name__,
                parameters=[vectorstore_id],
                status="202",
            )
        ),
        family.path("{id}/undeploy/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("undeploy"),
                f"Undeploy {family.a}",
                f"Stop serving the {resource}. A self-hosted server's data is kept. {owner}",
                tag,
                VectorstoreApiVectorstore.__name__,
                parameters=[vectorstore_id],
            )
        ),
        family.path("{id}/documents/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("documents"),
                f"{family.a_capitalized}'s documents",
                f"The {resource}'s documents, newest first, without their content.",
                tag,
                VectorstoreApiDocuments.__name__,
                many=False,
                parameters=[vectorstore_id],
                note=READ_PERMISSION,
            ),
            post=rest_operation(
                family.operation_id("add_documents"),
                f"Add documents to {family.a}",
                f"Add documents, and queue them to be loaded if the {resource} is ready: a text, the document at a "
                "url, or files as multipart/form-data, whose text is extracted now. A document whose content the "
                f"{resource} already has is a duplicate, and is not added again. {owner}",
                tag,
                VectorstoreApiDocumentsAdded.__name__,
                parameters=[vectorstore_id],
                status="202",
                request_body=OpenApiRequestBody(
                    required=True,
                    content={
                        "application/json": OpenApiMediaType(schema_=ref(VectorstoreApiAddText.__name__)),
                        "multipart/form-data": OpenApiMediaType(schema_=files),
                    },
                ),
            ),
        ),
        family.path("{id}/documents/{document_id}/"): OpenApiPathItem(
            delete=rest_operation(
                family.operation_id("delete_document"),
                f"Remove a document from {family.a}",
                f"Remove a document and its chunks. They are removed in the background. {owner}",
                tag,
                VectorstoreApiDocumentDeleted.__name__,
                parameters=[vectorstore_id, integer_id("document_id", "The document's id.")],
                status="202",
            )
        ),
        family.path("{id}/search/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("search"),
                f"Search {family.a}",
                f"Find the chunks most similar to a query. {READ_PERMISSION}",
                tag,
                VectorstoreApiSearchResults.__name__,
                parameters=[vectorstore_id],
                request_body=OpenApiRequestBody(
                    required=True,
                    description="The query, and how to search.",
                    content={"application/json": OpenApiMediaType(schema_=ref(VectorstoreApiSearch.__name__))},
                ),
            )
        ),
        family.path("{id}/snapshots/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("snapshots"),
                f"{family.a_capitalized}'s snapshots",
                f"The {resource}'s snapshots: Qdrant snapshots, or Pinecone backups.",
                tag,
                VectorstoreApiSnapshots.__name__,
                many=False,
                parameters=[vectorstore_id],
                note=READ_PERMISSION,
            ),
            post=rest_operation(
                family.operation_id("create_snapshot"),
                f"Snapshot {family.a}",
                f"Take a snapshot of the {resource}'s data now. {owner}",
                tag,
                VectorstoreApiSnapshot.__name__,
                parameters=[vectorstore_id],
                status="201",
            ),
        ),
        family.path("{id}/snapshots/{snapshot_id}/restore/"): OpenApiPathItem(
            post=rest_operation(
                family.operation_id("restore"),
                f"Restore {family.a}",
                f"Replace the {resource}'s data with one of its snapshots. {owner}",
                tag,
                VectorstoreApiRestored.__name__,
                parameters=[vectorstore_id, integer_id("snapshot_id", "The snapshot's id.")],
            )
        ),
    }


__all__ = ["VECTORSTORES", "vectorstore_paths"]
