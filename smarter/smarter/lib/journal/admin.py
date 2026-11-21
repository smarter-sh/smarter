"""
Django admin for the Smarter Journal, Smarter's audit log of its api.

Every request that Smarter answers with a
:class:`~smarter.lib.journal.http.SmarterJournaledJsonResponse` is journaled as a
:class:`~smarter.lib.journal.models.SAMJournal` entry: who made the request, the thing and command
it was for (e.g. ``Prompt`` and ``prompt``, or ``Guardrail`` and ``apply``), its status code, and two
documents. The request document is the http request as
:class:`~smarter.lib.django.http.serializers.HttpAuthenticatedRequestSerializer` serializes it: its
url, method, an allowlist of its headers, and its ``body``, parsed and with its credentials redacted.
The response document is the JSON body that Smarter returned.

This admin is for staff only (:class:`~smarter.apps.dashboard.admin.SmarterStaffOnlyModelAdmin`),
and is read-mostly: the documents are read-only. A staff user sees the entries of the users of their
own accounts; a superuser sees every entry. Its list shows each entry's who, what and when,
without reading the documents, which are stored compressed (see :mod:`smarter.lib.journal.storage`)
and read only when one entry is opened.

An entry's page also shows what was asked and what was answered, for the entries of a chat
completion, e.g. a request to ``/api/v1/prompts/passthrough/<provider>/``, or a prompt sent to a
deployed LLMClient:

- **Prompt**: the last ``user`` message in the request body's ``messages``, validated as the OpenAI
  SDK's :class:`~openai.types.chat.ChatCompletionMessageParam`.
- **Response text**: the first choice's message of the response's chat completion, validated as the
  OpenAI SDK's :class:`~openai.types.chat.ChatCompletion`. A passthrough prompt journals the completion
  itself, and a prompt to an LLMClient journals it inside its chat contract's ``data``
  (see :func:`completion_document`).

Both are empty for any other entry, and for the entries that were journaled before the request's
body was.
"""

import json
from collections.abc import Iterable
from typing import Union

from django.contrib import admin
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
)
from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from smarter.apps.account.models import UserProfile
from smarter.apps.dashboard.admin import (
    SmarterStaffOnlyModelAdmin,
    smarter_admin_account_ids,
    smarter_admin_user,
    smarter_restricted_admin_site,
)
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys
from smarter.lib.journal.models import DOCUMENT_FIELDS, SAMJournal


class ChatCompletionRequestBody(BaseModel):
    """
    The body of an OpenAI chat completion request, with the one field that the admin reads.

    The OpenAI SDK types a request's parameters as TypedDicts, not Pydantic models, so each message
    is validated as the SDK's :class:`~openai.types.chat.ChatCompletionMessageParam`. A message's
    list of content parts is validated lazily, as it is read. Extra fields, e.g. ``model`` and the
    providers' own, are allowed.
    """

    model_config = ConfigDict(extra="allow")

    messages: list[ChatCompletionMessageParam]


class ChatCompletionRequestDocument(BaseModel):
    """
    A journal entry's request document whose ``body`` is a chat completion request.

    The document's other fields, the url, method and headers, are allowed, and not read.
    """

    model_config = ConfigDict(extra="allow")

    body: ChatCompletionRequestBody


def user_message_text(content: Union[str, Iterable[ChatCompletionContentPartParam]]) -> str:
    """
    Return the text of a ``user`` message's ``content``.

    :param content: A string, or the message's content parts, of which only ``text`` parts have text.
    :returns: The text, with the text parts joined by newlines.
    :raises ValidationError: If a content part isn't one of the SDK's.
    """
    if isinstance(content, str):
        return content
    texts = []
    for part in content:
        if part["type"] == "text":
            texts.append(part["text"])
    text = "\n".join(texts)
    return text


def prompt_text(request: JsonValue) -> str:
    """
    Return the prompt of a journaled chat completion request: the last ``user`` message in its body.

    :param request: The entry's request document, whose ``body`` is the OpenAI chat completion request.
    :returns: The prompt, or an empty string if the body holds no valid chat messages, or no ``user``
        message.
    """
    try:
        document = ChatCompletionRequestDocument.model_validate(request)
        messages = document.body.messages
        for message in reversed(messages):
            if message["role"] == "user":
                text = user_message_text(message["content"])
                return text
    except ValidationError:
        return ""
    return ""


def completion_document(response: JsonValue) -> JsonValue:
    """
    Return the chat completion in a journaled response document.

    Smarter journals a chat completion in one of three envelopes:

    - a passthrough prompt, ``/api/v1/prompts/passthrough/<provider>/``: the completion itself, with
      Smarter's ``api`` and ``metadata`` beside its fields.
    - a prompt to an LLMClient, chat contract version 2: ``{"data": {"completion": {...}, ...}}``.
    - a prompt to an LLMClient, chat contract version 1: ``{"data": {"statusCode": ..., "body": ...}}``,
      whose body is the completion, as a dict or a JSON string, or, if the LLM provider failed,
      ``{"error": ..., "response": <the completion>}``.

    :param response: The entry's response document.
    :returns: The completion, or the response itself if it is in none of the LLMClient envelopes.
    """
    if not isinstance(response, dict):
        return response
    data = response.get(SmarterJournalApiResponseKeys.DATA)
    if not isinstance(data, dict):
        return response
    if "completion" in data:
        return data["completion"]
    body = data.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except ValueError:
            return None
    if isinstance(body, dict) and "error" in body:
        return body.get("response")
    return body


def response_text(response: JsonValue) -> str:
    """
    Return the reply of a journaled chat completion: its first choice's message.

    :param response: The entry's response document, in any of the envelopes that
        :func:`completion_document` reads.
    :returns: The reply, or an empty string if the response is not a chat completion, or its message
        has no content, e.g. only tool calls.
    """
    try:
        completion = ChatCompletion.model_validate(completion_document(response))
    except ValidationError:
        return ""
    if not completion.choices:
        return ""
    content = completion.choices[0].message.content
    if content is None:
        return ""
    return content


class SAMJournalAdmin(SmarterStaffOnlyModelAdmin):
    """
    The admin of :class:`~smarter.lib.journal.models.SAMJournal`.

    The list shows each entry's who, what and when. ``thing`` and ``command`` are choice fields, which
    the admin shows by their labels, and sorts by. An entry's page adds its prompt and the LLM's reply,
    read from its documents.
    """

    readonly_fields = ("created_at", "prompt", "reply", "request", "response")
    list_display = ("created_at", "user", "thing", "command", "status_code")
    raw_id_fields = ("user",)
    search_fields = ("key", "user__username", "user__email", "thing", "command")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    def get_queryset(self, request):
        """
        Return the entries the user may see, without their documents, which are read only when one entry is shown.

        A superuser sees every entry. A staff user sees the entries of the users of their own accounts.

        :param request: The admin's request.
        :returns: The entries.
        """
        queryset = super().get_queryset(request)
        queryset = queryset.defer(*DOCUMENT_FIELDS)
        user = smarter_admin_user(request)
        if user is None:
            return queryset.none()
        if user.is_superuser:
            return queryset
        account_users = UserProfile.objects.filter(account_id__in=smarter_admin_account_ids(user)).values("user_id")
        return queryset.filter(user_id__in=account_users)

    @admin.display(description="Prompt")
    def prompt(self, obj: SAMJournal) -> str:
        """
        Return the entry's prompt, e.g. ``What's the weather in San Francisco?``.

        :param obj: The journal entry.
        :returns: The prompt, or an empty string if the entry is not a prompt.
        """
        return prompt_text(obj.request)

    @admin.display(description="Response text")
    def reply(self, obj: SAMJournal) -> str:
        """
        Return the LLM's reply to the entry's prompt, e.g. ``It's 63F right now``.

        :param obj: The journal entry.
        :returns: The reply, or an empty string if the response is not a chat completion.
        """
        return response_text(obj.response)


smarter_restricted_admin_site.register(SAMJournal, SAMJournalAdmin)
