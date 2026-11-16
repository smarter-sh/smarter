"""Serializers for the Smarter Journal api."""

from typing import Union

from rest_framework import serializers

from smarter.apps.account.models import User
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import SAMJournal


class SAMJournalSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the :class:`smarter.lib.journal.models.SAMJournal` model: a complete journal entry.

    The entry's ``request`` and ``response`` documents are included. They hold user content, e.g. prompts
    and manifests, so this serializer is only used for one entry at a time, by superusers. The request
    document never holds the caller's cookies or api key: see
    :class:`~smarter.lib.django.http.serializers.HttpAnonymousRequestSerializer`. See :class:`SAMJournalMiniSerializer` for lists.

    **Fields:**

    - ``key`` (string): The entry's primary key, 64 hexadecimal characters.
    - ``createdAt`` (datetime): When the entry was written.
    - ``user`` (string): The username of the user who made the request, or null for an anonymous request.
    - ``thing`` (string): The kind of resource, e.g. Guardrail.
    - ``command`` (string): The command, e.g. apply.
    - ``request`` (JSON): The serialized http request.
    - ``response`` (JSON): The response's JSON body.
    - ``statusCode`` (integer): The response's http status.

    .. note::

            All fields are read-only. Smarter never changes a journal entry.

    **Example usage**::

        from smarter.lib.journal.serializers import SAMJournalSerializer
        data = SAMJournalSerializer(journal).data
    """

    # what SlugRelatedField() returns: DRF's RelatedField.__new__ makes a ManyRelatedField when many=True.
    user: "Union[serializers.RelatedField[User, str, str], serializers.ManyRelatedField]" = (
        serializers.SlugRelatedField(read_only=True, slug_field="username")
    )

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SAMJournal
        fields = ["key", "created_at", "user", "thing", "command", "request", "response", "status_code"]
        read_only_fields = fields


class SAMJournalMiniSerializer(SmarterCamelCaseSerializer):
    """
    Minimal serializer for the :class:`smarter.lib.journal.models.SAMJournal` model, without the entry's request and response documents.

    It is used to list journal entries, whose documents can be large, and hold user content.

    **Fields:**

    - ``key`` (string): The entry's primary key.
    - ``createdAt`` (datetime): When the entry was written.
    - ``user`` (string): The username of the user who made the request, or null for an anonymous request.
    - ``thing`` (string): The kind of resource, e.g. Guardrail.
    - ``command`` (string): The command, e.g. apply.
    - ``statusCode`` (integer): The response's http status.

    **Example usage**::

        from smarter.lib.journal.serializers import SAMJournalMiniSerializer
        data = SAMJournalMiniSerializer(journals, many=True).data
    """

    # what SlugRelatedField() returns: DRF's RelatedField.__new__ makes a ManyRelatedField when many=True.
    user: "Union[serializers.RelatedField[User, str, str], serializers.ManyRelatedField]" = (
        serializers.SlugRelatedField(read_only=True, slug_field="username")
    )

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SAMJournal
        fields = ["key", "created_at", "user", "thing", "command", "status_code"]
        read_only_fields = fields
