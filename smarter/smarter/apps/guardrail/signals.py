"""
Signals for the guardrail app.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.dispatch import Signal

guardrail_called = Signal()
"""
Signal sent when a Guardrail api endpoint is called.

Arguments:
    guardrail (Guardrail): The guardrail.
    request (HttpRequest): The HTTP request object.

Example::

    guardrail_called.send(sender=self.__class__, guardrail=guardrail, request=request)
"""

guardrail_triggered = Signal()
"""
Signal sent when a guardrail triggers, whatever its action.

Arguments:
    guardrail (Guardrail): The guardrail.
    stage (str): input or output.
    disposition (str): What the guardrail did, a GuardrailDisposition value.
    event (GuardrailEvent | None): The recorded event.

Example::

    guardrail_triggered.send(sender=self.__class__, guardrail=guardrail, stage="input", disposition="redacted", event=event)
"""

guardrail_blocked = Signal()
"""
Signal sent when a guardrail blocks the user's message or the LLM's reply.

Arguments:
    guardrail (Guardrail): The guardrail.
    stage (str): input or output.
    message (str): The message returned to the user.
    event (GuardrailEvent | None): The recorded event.

Example::

    guardrail_blocked.send(sender=self.__class__, guardrail=guardrail, stage="input", message=message, event=event)
"""

guardrail_escalated = Signal()
"""
Signal sent when a guardrail escalates to human review.

Connect a receiver to notify reviewers,
e.g. by email or chat.

Arguments:
    guardrail (Guardrail): The guardrail.
    stage (str): input or output.
    event (GuardrailEvent | None): The recorded event, which awaits review.

Example::

    guardrail_escalated.send(sender=self.__class__, guardrail=guardrail, stage="input", event=event)
"""

guardrail_failed = Signal()
"""
Signal sent when a guardrail fails to run, e.g. because its LLM provider is unavailable.

Arguments:
    guardrail (Guardrail): The guardrail.
    stage (str): input or output.
    error (str): A description of the error.
    fail_closed (bool): Whether the failure blocked the prompt.

Example::

    guardrail_failed.send(sender=self.__class__, guardrail=guardrail, stage="input", error=error, fail_closed=False)
"""
