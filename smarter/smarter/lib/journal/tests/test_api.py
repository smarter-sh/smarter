"""Test the Smarter Journal api: :mod:`smarter.lib.journal.api.v1.views`."""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.shortcuts import reverse
from smarter.lib.journal.api.v1.urls import SAMJournalApiV1ReverseViews
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.models import SAMJournal

LIST_URL = f"{SAMJournalApiV1ReverseViews.namespace}:{SAMJournalApiV1ReverseViews.list_view}"
DETAIL_URL = f"{SAMJournalApiV1ReverseViews.namespace}:{SAMJournalApiV1ReverseViews.journal_view}"


class TestSAMJournalApi(TestAccountMixin):
    """Test the journal's list and detail views, which only superusers may call."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = SAMJournal.objects.create(
            user=cls.admin_user,
            thing=SmarterJournalThings.GUARDRAIL.value,
            command=SmarterJournalCliCommands.APPLY.value,
            request={"url": "http://localhost:9357/api/v1/cli/apply/"},
            response={"data": {"a": 1}},
            status_code=HTTPStatus.OK,
        )

    @classmethod
    def tearDownClass(cls):
        cls.journal.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = Client()

    def superuser_client(self) -> Client:
        # admin_user_factory() creates a superuser.
        self.client.force_login(self.admin_user)
        return self.client

    def test_detail(self):
        with patch("smarter.lib.journal.api.v1.views.journal_entry_accessed.send") as send:
            for method in ("get", "post"):
                with self.subTest(method=method):
                    response = getattr(self.superuser_client(), method)(
                        reverse(DETAIL_URL, kwargs={"key": self.journal.key})
                    )
                    self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                    data = response.json()
                    self.assertEqual(data["key"], self.journal.key)
                    self.assertEqual(data["user"], self.admin_user.username)
                    self.assertEqual(data["thing"], "Guardrail")
                    self.assertEqual(data["statusCode"], 200)
                    self.assertEqual(data["response"], {"data": {"a": 1}})
        self.assertEqual(send.call_count, 2)

    def test_detail_not_found(self):
        response = self.superuser_client().get(reverse(DETAIL_URL, kwargs={"key": "0" * 64}))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_list(self):
        with patch("smarter.lib.journal.api.v1.views.journal_entries_listed.send") as send:
            response = self.superuser_client().get(
                reverse(LIST_URL), {"search": self.journal.key, "ordering": "-statusCode"}
            )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        data = response.json()
        self.assertEqual(data["pagination"]["count"], 1)
        self.assertEqual(data["pagination"]["ordering"], "-statusCode")
        self.assertIn("statusCode", data["pagination"]["sortFields"])
        entry = data["objects"][0]
        self.assertEqual(entry["key"], self.journal.key)
        # the list never includes an entry's documents, which hold credentials.
        self.assertNotIn("request", entry)
        self.assertNotIn("response", entry)
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["count"], 1)

    def test_list_post(self):
        response = self.superuser_client().post(reverse(LIST_URL) + f"?search={self.journal.key}")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertEqual(response.json()["pagination"]["count"], 1)

    def test_non_superuser_is_forbidden(self):
        self.client.force_login(self.non_admin_user)
        for url in (reverse(LIST_URL), reverse(DETAIL_URL, kwargs={"key": self.journal.key})):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))

    def test_anonymous_is_refused(self):
        for url in (reverse(LIST_URL), reverse(DETAIL_URL, kwargs={"key": self.journal.key})):
            with self.subTest(url=url):
                response = Client().get(url)
                self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))
