"""Constants for the web console's api."""

from smarter.apps.api.const import namespace as api_namespace

namespace = "web"
"""The url namespace of the web console's api, mounted at ``/api/web/``."""

path_namespace = f"{api_namespace}:{namespace}"
"""
The web console api's namespaces from the root urlconf, ``api:web``.

An app's ``api/web/urls.py`` prefixes its own namespace with it, e.g.
``f"{path_namespace}:{namespace}"`` is ``api:web:guardrail``.
"""
