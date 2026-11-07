"""
URL configuration of the docs app, ``/docs/``: the pages of the example manifests, the JSON Schemas and the OpenAPI.

document, which the single-page console shows (see :mod:`smarter.apps.docs.views.views`), and the OpenAPI
document's earlier address.
"""

from django.shortcuts import redirect
from django.urls import path

from .const import namespace
from .views.openapi import DocsOpenApiJsonView, DocsOpenApiView
from .views.views import (
    DocsExampleManifestsView,
    DocsExampleManifestView,
    DocsJsonSchemasView,
    DocsJsonSchemaView,
)


class DocsReverseNames:
    """The names of the docs app's urls, e.g. ``reverse(DocsReverseNames.namespace, DocsReverseNames.openapi)``."""

    namespace = namespace
    example_manifests = "example_manifests"
    example_manifest = "example_manifest"
    openapi = "openapi"
    openapi_json = "openapi-json"
    json_schemas = "json_schemas"
    json_schema = "json_schema"


app_name = namespace
urlpatterns = [
    path("", lambda request: redirect(namespace + ":example_manifests", permanent=False), name="docs-home"),
    # the OpenAPI document's page, and its earlier address, which redirects to the api's.
    path("openapi/", DocsOpenApiView.as_view(), name=DocsReverseNames.openapi),
    path("openapi.json", DocsOpenApiJsonView.as_view(), name=DocsReverseNames.openapi_json),
    # the example manifests, and each kind's, e.g. /docs/manifest/llmclient/, which the smarter cli's help links.
    path("manifests/", DocsExampleManifestsView.as_view(), name=DocsReverseNames.example_manifests),
    path("manifest/<str:kind>/", DocsExampleManifestView.as_view(), name=DocsReverseNames.example_manifest),
    # the JSON Schemas, and each kind's, e.g. /docs/json-schema/llmclient/.
    path("json-schemas/", DocsJsonSchemasView.as_view(), name=DocsReverseNames.json_schemas),
    path("json-schema/<str:kind>/", DocsJsonSchemaView.as_view(), name=DocsReverseNames.json_schema),
]
