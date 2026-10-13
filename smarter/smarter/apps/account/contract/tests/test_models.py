"""Test :mod:`smarter.apps.account.contract.models`, and the accounts' real responses against the OpenAPI document."""

import json
from datetime import datetime
from http import HTTPStatus

from pydantic import ValidationError
from rest_framework.test import APIClient

from smarter.apps.account.contract.models import (
    AccountApiAccountDetail,
    AccountApiContact,
    AccountApiProfile,
    AccountApiUserDetail,
    AccountApiUserProfile,
)
from smarter.apps.account.models import AccountContact
from smarter.apps.account.serializers import (
    AccountContactSerializer,
    AccountSerializer,
    UserProfileSerializer,
    UserSerializer,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin


class TestAccountContractModels(TestAccountMixin):
    """Test the account contract's models against the serializer whose output they replace."""

    def test_user_profile_is_the_serializers_output(self):
        model = AccountApiUserProfile.from_model(self.user_profile)
        self.assertEqual(model.model_dump(mode="json"), dict(UserProfileSerializer(self.user_profile).data))
        self.assertEqual(model.account.account_number, self.account.account_number)

    def test_aliases(self):
        data = {"user": {"username": "u", "email": None}, "account": {"accountNumber": "1234-5678-9012"}}
        self.assertEqual(AccountApiUserProfile.model_validate(data).model_dump(mode="json"), data)

    def test_extra_fields_are_forbidden(self):
        with self.assertRaises(ValidationError):
            AccountApiUserProfile.model_validate(
                {"user": {"username": "u"}, "account": {"accountNumber": "1"}, "id": 1}
            )


class TestAccountApiContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the accounts' REST models against the serializers, and the views' responses against the document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # welcomed, so that saving it sends no welcome email.
        cls.contact = AccountContact.objects.create(
            account=cls.account,
            first_name="Test",
            last_name="Contact",
            email=f"contact-{cls.hash_suffix}@mail.com",
            is_test=True,
            welcomed=True,
        )

    @classmethod
    def tearDownClass(cls):
        AccountContact.objects.filter(pk=cls.contact.pk).delete()
        super().tearDownClass()

    def serialized(self, serializer_class, row) -> dict:
        return json.loads(json.dumps(serializer_class(row).data, default=str))

    def assertSameJson(self, model: dict, serialized: dict):
        """Compare a model's dump with a serializer's output, whose datetimes are formatted differently."""
        for key in set(model) | set(serialized):
            value = model.get(key)
            other = serialized.get(key)
            if key in ("createdAt", "updatedAt") and value and other:
                self.assertEqual(datetime.fromisoformat(value), datetime.fromisoformat(other), key)
            else:
                self.assertEqual(value, other, key)

    def test_models_are_the_serializers_output(self):
        self.assertSameJson(
            AccountApiAccountDetail.from_model(self.account).model_dump(mode="json"),
            self.serialized(AccountSerializer, self.account),
        )
        self.assertSameJson(
            AccountApiUserDetail.from_model(self.admin_user).model_dump(mode="json"),
            self.serialized(UserSerializer, self.admin_user),
        )
        self.assertSameJson(
            AccountApiContact.from_model(self.contact).model_dump(mode="json"),
            self.serialized(AccountContactSerializer, self.contact),
        )

    def test_profile(self):
        profile = AccountApiProfile.from_model(self.user_profile)
        self.assertEqual(profile.user.username, self.admin_user.username)
        self.assertEqual(profile.account.account_number, self.account.account_number)
        self.assertIn("isTest", profile.model_dump(mode="json"))

    def test_responses(self):
        client = APIClient()
        client.force_login(self.admin_user)
        for template, path in {
            "/accounts/": "/accounts/",
            "/accounts/{account_id}/": f"/accounts/{self.account.pk}/",
            "/accounts/users/": "/accounts/users/",
            "/accounts/users/{user_id}/": f"/accounts/users/{self.non_admin_user.pk}/",
            "/accounts/user-profiles/": "/accounts/user-profiles/",
            "/accounts/user-profiles/{user_profile_id}/": f"/accounts/user-profiles/{self.user_profile.pk}/",
            "/accounts/contacts/": "/accounts/contacts/",
            "/accounts/contacts/{account_contact_id}/": f"/accounts/contacts/{self.contact.pk}/",
        }.items():
            with self.subTest(path=template):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                self.assertValidResponse(template, "get", response.json())
        response = client.get(f"/api/v1/accounts/user-profiles/{self.user_profile.pk}/")
        self.assertEqual(response.json()["id"], self.user_profile.pk)
        response = client.get("/api/v1/accounts/users/999999999/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertValidResponse("/accounts/users/{user_id}/", "get", response.json(), HTTPStatus.NOT_FOUND)

    def test_superusers_only(self):
        client = APIClient()
        client.force_login(self.non_admin_user)
        response = client.get("/api/v1/accounts/users/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertValidResponse("/accounts/users/", "get", response.json(), HTTPStatus.FORBIDDEN)
