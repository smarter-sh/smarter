"""Signals of ApiPlugin tool calls."""

from django.dispatch import Signal

api_plugin_request_started = Signal()
"""
Signal sent when a ApiPlugin tool call begins: a remote API request.

Arguments:
    plugin: The ApiPlugin instance.
    function_args: The tool call's arguments, as the LLM sent them.

Example::

    api_plugin_request_started.send(sender=self.__class__, plugin=self, function_args=function_args)
"""

api_plugin_authenticated = Signal()
"""
Signal sent when the plugin's remote API accepts the request's credentials, that is, responds with any status other than HTTP 401 or 403.

Not sent when the response is served from the cache.

Arguments:
    plugin: The ApiPlugin instance.
    connection: The name of the ApiConnection.
    auth_method: The ApiConnection's authentication method, e.g. ``none``, ``basic`` or ``token``.
    status_code: The HTTP status code of the response.

Example::

    api_plugin_authenticated.send(sender=self.__class__, plugin=self, connection="stackademy", auth_method="token", status_code=200)
"""

api_plugin_authentication_failed = Signal()
"""
Signal sent when the plugin's remote API rejects the request's credentials, with HTTP 401 or 403.

Arguments:
    plugin: The ApiPlugin instance.
    connection: The name of the ApiConnection.
    auth_method: The ApiConnection's authentication method.
    status_code: The HTTP status code of the response.
    error: What went wrong.

Example::

    api_plugin_authentication_failed.send(sender=self.__class__, plugin=self, connection="stackademy", auth_method="token", status_code=401, error="HTTP 401")
"""

api_plugin_responded = Signal()
"""
Signal sent when a ApiPlugin tool call returns its response to the LLM.

Arguments:
    plugin: The ApiPlugin instance.
    response: The JSON response, as a dict or list, or an empty string if it was empty.
    cached: True if the response was served from the cache.
    method: The HTTP method.
    endpoint: The endpoint, with its placeholders interpolated.

Example::

    api_plugin_responded.send(sender=self.__class__, plugin=self, response=[{"id": 1}], cached=False, method="GET", endpoint="/v1/courses/")
"""

api_plugin_failed = Signal()
"""
Signal sent when a ApiPlugin tool call fails, whether it raises or returns an empty response to the LLM.

Arguments:
    plugin: The ApiPlugin instance.
    error: What went wrong. It never contains credentials.

Example::

    api_plugin_failed.send(sender=self.__class__, plugin=self, error="API request failed: GET /v1/courses/")
"""

api_plugin_request_completed = Signal()
"""
Signal sent when a ApiPlugin tool call ends, successfully or not.

It is always the last signal of the call.

Arguments:
    plugin: The ApiPlugin instance.
    success: False if api_plugin_failed was sent.
    duration: The seconds that the tool call took.

Example::

    api_plugin_request_completed.send(sender=self.__class__, plugin=self, success=True, duration=0.42)
"""
