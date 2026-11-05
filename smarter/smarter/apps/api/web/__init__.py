"""
The web console's api, mounted at ``/api/web/``.

This is the backend half of Smarter's Django-React integration
(:doc:`/smarter-framework/developer-reference/react-integration`). These are the endpoints that
the web console's React apps call: the list, clone, rename and
delete actions of each resource list page, the dashboard's widgets, and the like. They are
internal to the console. Unlike ``/api/v1/``, they carry no compatibility promise, they are
not in the OpenAPI document, and they authenticate with the browser's Django session and CSRF
token. See :doc:`/adr/034-web-console-api` and :doc:`/smarter-framework/developer-reference/web-console-api`.
"""
