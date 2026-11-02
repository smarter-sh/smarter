"""
Help desk tools: what the platform knows about one user's problem, and a check of the reply to them.

- :mod:`~smarter.apps.mcpserver.helpdesk.users`: the state of a user's account, their failed sign-ins
  from the pod logs, and their recent failed requests from the journal.
- :mod:`~smarter.apps.mcpserver.helpdesk.replies`: the rules that a reply to a user must follow, and
  the check that finds where a draft breaks them.
- :mod:`~smarter.apps.mcpserver.helpdesk.tools`: ``user_support_snapshot`` and ``check_reply``.

Only these tools read one user's own data, so the rules about personal data are kept here, in one place.
"""
