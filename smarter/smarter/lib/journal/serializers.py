"""Serializers for the Smarter Journal api."""

from rest_framework import serializers

from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import SAMJournal


class SAMJournalSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the :class:`smarter.lib.journal.models.SAMJournal` model: a complete journal entry.

    The entry's ``request`` and ``response`` documents are included. The request document holds the
    caller's headers and cookies, including its api key, so this serializer is only used for one entry
    at a time, by superusers. See :class:`SAMJournalMiniSerializer` for lists.

    :param key: String. The entry's primary key, 64 hexadecimal characters.
    :param created_at: DateTime. When the entry was written.
    :param user: String. The username of the user who made the request, or null for an anonymous request.
    :param thing: String. The kind of resource, e.g. Guardrail.
    :param command: String. The command, e.g. apply.
    :param request: JSON. The serialized http request.
    :param response: JSON. The response's JSON body.
    :param status_code: Integer. The response's http status.

    .. note::

            All fields are read-only. Smarter never changes a journal entry.

    **Example usage**::

        from smarter.lib.journal.serializers import SAMJournalSerializer
        data = SAMJournalSerializer(journal).data
    """

    user = serializers.SlugRelatedField(read_only=True, slug_field="username")

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SAMJournal
        fields = ["key", "created_at", "user", "thing", "command", "request", "response", "status_code"]
        read_only_fields = fields


class SAMJournalMiniSerializer(SmarterCamelCaseSerializer):
    """
    Minimal serializer for the :class:`smarter.lib.journal.models.SAMJournal` model, without the entry's request and response documents.

    It is used to list journal entries, which can be large, and whose documents hold credentials.

    :param key: String. The entry's primary key.
    :param created_at: DateTime. When the entry was written.
    :param user: String. The username of the user who made the request, or null for an anonymous request.
    :param thing: String. The kind of resource, e.g. Guardrail.
    :param command: String. The command, e.g. apply.
    :param status_code: Integer. The response's http status.

    **Example usage**::

        from smarter.lib.journal.serializers import SAMJournalMiniSerializer
        data = SAMJournalMiniSerializer(journals, many=True).data
    """

    user = serializers.SlugRelatedField(read_only=True, slug_field="username")

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SAMJournal
        fields = ["key", "created_at", "user", "thing", "command", "status_code"]
        read_only_fields = fields
