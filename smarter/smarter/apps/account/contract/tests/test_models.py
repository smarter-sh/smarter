"""Test :mod:`smarter.apps.account.contract.models`."""

from pydantic import ValidationError

from smarter.apps.account.contract.models import AccountApiUserProfile
from smarter.apps.account.serializers import UserProfileSerializer
from smarter.apps.account.tests.mixins import TestAccountMixin


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
