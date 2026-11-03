"""
The help desk: what the platform knows about one user's problem, and a check of the reply to them.

- :mod:`~smarter.apps.mcpserver.services.helpdesk.users`: the state of a user's account, their
  failed sign-ins from the pod logs, and their recent failed requests from the journal.
- :mod:`~smarter.apps.mcpserver.services.helpdesk.replies`: the rules that a reply to a user must
  follow, and the check that finds where a draft breaks them.

Only these services read one user's own data, so the rules about personal data are kept here, in one place.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
