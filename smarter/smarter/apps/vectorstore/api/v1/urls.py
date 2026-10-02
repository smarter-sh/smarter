"""
URL configuration for the Vectorstore app API.

These are mounted at ``/api/v1/vectorstores/``. See :mod:`smarter.apps.vectorstore.api.v1.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views import (
    VectorstoreDeployView,
    VectorstoreDocumentsView,
    VectorstoreDocumentView,
    VectorstoreListView,
    VectorstoreRestoreView,
    VectorstoreSearchView,
    VectorstoreSnapshotsView,
    VectorstoreStatusView,
    VectorstoreUndeployView,
    VectorstoreView,
)

app_name = namespace
BY_ID = "_by_id"
BY_HASHED_ID = "_by_hashed_id"

PER_VECTORSTORE = {
    "": VectorstoreView,
    "status/": VectorstoreStatusView,
    "deploy/": VectorstoreDeployView,
    "undeploy/": VectorstoreUndeployView,
    "documents/": VectorstoreDocumentsView,
    "documents/<int:document_id>/": VectorstoreDocumentView,
    "search/": VectorstoreSearchView,
    "snapshots/": VectorstoreSnapshotsView,
    "snapshots/<int:snapshot_id>/restore/": VectorstoreRestoreView,
}
"""The views of one vectorstore, by URL suffix."""


class VectorstoreApiV1ReverseViews:
    """
    Reverse view names of the Vectorstore api.

    Each is available by the vectorstore's hashed id, and by its id.

    .. code-block:: python

        url = reverse(
            f"{VectorstoreApiV1ReverseViews.namespace}:{VectorstoreApiV1ReverseViews.search_by_hashed_id}",
            kwargs={"hashed_id": vectorstore.hashed_id},
        )
    """

    namespace = "api:v1:vectorstore"
    list_view = to_snake_case(VectorstoreListView.__name__)
    vectorstore_by_hashed_id = to_snake_case(VectorstoreView.__name__) + BY_HASHED_ID
    status_by_hashed_id = to_snake_case(VectorstoreStatusView.__name__) + BY_HASHED_ID
    deploy_by_hashed_id = to_snake_case(VectorstoreDeployView.__name__) + BY_HASHED_ID
    undeploy_by_hashed_id = to_snake_case(VectorstoreUndeployView.__name__) + BY_HASHED_ID
    documents_by_hashed_id = to_snake_case(VectorstoreDocumentsView.__name__) + BY_HASHED_ID
    document_by_hashed_id = to_snake_case(VectorstoreDocumentView.__name__) + BY_HASHED_ID
    search_by_hashed_id = to_snake_case(VectorstoreSearchView.__name__) + BY_HASHED_ID
    snapshots_by_hashed_id = to_snake_case(VectorstoreSnapshotsView.__name__) + BY_HASHED_ID
    restore_by_hashed_id = to_snake_case(VectorstoreRestoreView.__name__) + BY_HASHED_ID


urlpatterns = [path("", VectorstoreListView.as_view(), name=VectorstoreApiV1ReverseViews.list_view)]
for suffix, view in PER_VECTORSTORE.items():
    view_name = to_snake_case(view.__name__)
    urlpatterns += [
        path(f"<int:vectorstore_id>/{suffix}", view.as_view(), name=view_name + BY_ID),
        path(f"<str:hashed_id>/{suffix}", view.as_view(), name=view_name + BY_HASHED_ID),
    ]
