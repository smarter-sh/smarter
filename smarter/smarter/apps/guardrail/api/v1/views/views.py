# pylint: disable=W0718,W0613
"""
Guardrail api/v1/guardrails views.

Guardrails are created and updated by applying manifests, with ``smarter apply``, so these
views do not create or update them:

- ``GET guardrails/``: the Guardrails that the user may read, including the built-in ones.
- ``GET guardrails/<hashed_id>/``: a Guardrail that the user may read.
- ``DELETE guardrails/<hashed_id>/``: delete a Guardrail that the user owns.
- ``POST guardrails/<hashed_id>/evaluate/``: dry-run a Guardrail on a text, e.g. to test a new
  guardrail. The JSON body is ``{"text": "...", "stage": "input"}``. It records no events.
- ``GET guardrails/<hashed_id>/events/``: the latest events of a Guardrail that the user owns.

The responses are built from the models of :mod:`smarter.apps.guardrail.contract.models`, which the
Smarter api's OpenAPI document publishes. Errors are Django REST framework's ``{"detail": ...}``.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus
from typing import Any

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.exceptions import ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.guardrail.caching import (
    invalidate_all_cached_guardrails_for_user_profile,
)
from smarter.apps.guardrail.contract.models import (
    GuardrailApiEvaluation,
    GuardrailApiEvent,
    GuardrailApiEvents,
    GuardrailApiFinding,
    GuardrailApiGuardrail,
)
from smarter.apps.guardrail.models import Guardrail, GuardrailStage
from smarter.apps.guardrail.serializers import GuardrailSerializer
from smarter.apps.guardrail.services import GuardrailPipeline
from smarter.apps.guardrail.signals import guardrail_called
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])

MAX_EVALUATE_LENGTH = 20000
"""The maximum length of the text of a dry run."""
MAX_EVENTS = 100
"""The maximum number of events returned."""


def evaluate(guardrail: Guardrail, text: str, stage: str) -> GuardrailApiEvaluation:
    """
    Dry-run a guardrail on a text, as the user's message (input) or the LLM's reply (output).

    :returns: Whether it triggered, the disposition, the text after its action, and its findings.
    :rtype: GuardrailApiEvaluation
    """
    pipeline = GuardrailPipeline([guardrail], record_events=False)
    if stage == GuardrailStage.INPUT:
        result = pipeline.run_pre({"messages": [{"role": "user", "content": text}]})
        output = result.payload["messages"][0]["content"]
    else:
        result = pipeline.run_post({"choices": [{"index": 0, "message": {"role": "assistant", "content": text}}]})
        output = result.payload["choices"][0]["message"]["content"]
    outcome = result.outcomes[0] if result.outcomes else None
    return GuardrailApiEvaluation(
        guardrail=guardrail.name,
        stage=stage,  # type: ignore[arg-type]
        triggered=bool(result.triggered_findings),
        disposition=result.disposition,
        text=output,
        message=result.fallback_message,
        error=outcome.error if outcome else None,
        duration_ms=outcome.duration_ms if outcome else None,
        findings=[
            GuardrailApiFinding(confidence=finding.confidence, rationale=finding.rationale, matches=finding.matches)
            for finding in result.triggered_findings
        ],
    )


class GuardrailViewBase(SmarterAuthenticatedAPIView):
    """
    Base class for views of one Guardrail, identified by ``hashed_id`` or ``guardrail_id``.

    :meth:`get_guardrail` returns the Guardrail only if the user may read it, or, with
    ``owner=True``, only if the user owns it. Otherwise it raises :class:`~django.http.Http404`,
    so that the Guardrails of other accounts are not disclosed.
    """

    def get_guardrail(self, request: Request, owner: bool = False, **kwargs) -> Guardrail:
        """Return the Guardrail in the URL, if the user may read it, or own it."""
        hashed_id = kwargs.get("hashed_id")
        guardrail_id = Guardrail.id_from_hashed_id(hashed_id) if hashed_id else kwargs.get("guardrail_id")
        if not guardrail_id:
            raise Http404("Guardrail not found")
        queryset = (
            Guardrail.objects.with_ownership_permission_for(user=request.user)  # type: ignore[attr-defined]
            if owner
            else Guardrail.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        )
        guardrail = queryset.select_related("user_profile__user").filter(pk=guardrail_id).first()
        if guardrail is None:
            raise Http404("Guardrail not found")
        guardrail_called.send(sender=self.__class__, guardrail=guardrail, request=request)
        return guardrail


class GuardrailView(GuardrailViewBase):
    """Read or delete a Guardrail."""

    serializer_class = GuardrailSerializer

    def get(self, request: Request, *args, **kwargs):
        """Return a Guardrail that the user may read."""
        guardrail = self.get_guardrail(request, **kwargs)
        return Response(GuardrailApiGuardrail.from_model(guardrail, request.user).model_dump(mode="json"))

    def delete(self, request: Request, *args, **kwargs):
        """Delete a Guardrail that the user owns."""
        guardrail = self.get_guardrail(request, owner=True, **kwargs)
        user_profile = guardrail.user_profile
        guardrail.delete()
        if user_profile:
            invalidate_all_cached_guardrails_for_user_profile(user_profile)
        return Response(status=HTTPStatus.NO_CONTENT)


class GuardrailEvaluateView(GuardrailViewBase):
    """Dry-run a Guardrail on a text."""

    def post(self, request: Request, *args, **kwargs):
        """Dry-run the Guardrail on the JSON body's ``text``, as the ``stage`` ``input`` (default) or ``output``."""
        guardrail = self.get_guardrail(request, **kwargs)
        data = request.data if isinstance(request.data, dict) else {}
        text = data.get("text")
        stage = str(data.get("stage") or GuardrailStage.INPUT)
        if not isinstance(text, str) or not text:
            raise ParseError("text is required.")
        if len(text) > MAX_EVALUATE_LENGTH:
            raise ParseError(f"text must be at most {MAX_EVALUATE_LENGTH} characters.")
        if stage not in (GuardrailStage.INPUT, GuardrailStage.OUTPUT):
            raise ParseError("stage must be input or output.")
        if not guardrail.runs_on(stage):
            raise ParseError(f"Guardrail {guardrail.name} does not run on {stage}.")
        return Response(evaluate(guardrail, text, stage).model_dump(mode="json"))


class GuardrailEventsView(GuardrailViewBase):
    """The latest events of a Guardrail that the user owns."""

    def get(self, request: Request, *args, **kwargs):
        """Return the latest events, optionally filtered by ``?reviewed=true|false`` and ``?disposition=``."""
        guardrail = self.get_guardrail(request, owner=True, **kwargs)
        events = guardrail.events.select_related("llmclient").all()  # type: ignore[attr-defined]
        reviewed = request.query_params.get("reviewed")
        if reviewed in ("true", "false"):
            events = events.filter(reviewed=reviewed == "true")
        disposition = request.query_params.get("disposition")
        if disposition:
            events = events.filter(disposition=disposition)
        rows = events.order_by("-created_at")[:MAX_EVENTS]
        response = GuardrailApiEvents(
            guardrail=guardrail.name, events=[GuardrailApiEvent.from_model(row) for row in rows]
        )
        return Response(response.model_dump(mode="json"))


class GuardrailListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The Guardrails that the user may read."""

    serializer_class = GuardrailSerializer
    contract_model = GuardrailApiGuardrail

    def item(self, row):
        """A Guardrail of the response, whose ``canDelete`` is the requesting user's."""
        return GuardrailApiGuardrail.from_model(row, self.request.user).model_dump(mode="json")

    def get_queryset(self, *args, **kwargs) -> QuerySet[Guardrail]:
        return Guardrail.objects.with_read_permission_for(user=self.request.user).order_by("priority", "name")  # type: ignore[attr-defined]
