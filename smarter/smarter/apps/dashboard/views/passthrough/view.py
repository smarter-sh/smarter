"""
The Prompt Passthrough page: the single-page console's (ADR-035).

The page sends a raw JSON request, formatted for an LLM provider's api, through the Smarter prompt passthrough api,
``/api/v1/prompts/passthrough/<provider name>/``, and shows the provider's response. The console renders
``@smarter/prompt-passthrough`` at ``/dashboard/passthrough``, with the passthrough api's url, the providers api's,
``/api/web/dashboard/passthrough/providers/``, and, while users can view their server logs (see
:func:`smarter.apps.dashboard.views.terminal_emulator.enabled.server_logs_enabled`), the log stream's, from which the
page's Server Logs tab streams the server logs of each prompt that it sends.

Django keeps :class:`PromptPassthroughView` at the path it served the page at, so that its url name still reverses.

Example:
    Wire up the view in your URL configuration::

        from smarter.apps.dashboard.views.passthrough.view import PromptPassthroughView

        urlpatterns = [
            path("", PromptPassthroughView.as_view(), name="prompt_passthrough_view"),
        ]
"""

from smarter.apps.dashboard.views.console_app import ConsoleAppView


class PromptPassthroughView(ConsoleAppView):
    """
    The Prompt Passthrough page, ``/dashboard/passthrough/``: the single-page console's.

    The page exists only while ``smarter_settings.enable_dashboard_passthrough_prompt`` is set: otherwise its url is
    not registered, and the console's session says that the page is off, so that the console shows its Page not found.
    """
