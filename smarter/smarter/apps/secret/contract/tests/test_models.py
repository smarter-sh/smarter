"""Test :mod:`smarter.apps.secret.contract.models`."""

import json

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.contract.models import SecretApiSecret
from smarter.apps.secret.serializers import SecretSerializer
from smarter.apps.secret.tests.factories import secret_factory

VALUE = "not-a-real-secret-value"


class TestSecretContractModels(TestAccountMixin):
    """Test the Secret contract's model against the serializer whose output it replaces."""

    def setUp(self):
        super().setUp()
        self.secret = secret_factory(self.user_profile, "test_secret_contract_models", "A test secret.", VALUE)
        self.addCleanup(self.secret.delete)

    def test_secret_is_the_serializers_output(self):
        model = SecretApiSecret.from_model(self.secret)
        self.assertEqual(
            model.model_dump(mode="json"), json.loads(json.dumps(SecretSerializer(self.secret).data, default=str))
        )

    def test_value_is_never_returned(self):
        data = json.dumps(SecretApiSecret.from_model(self.secret, self.admin_user).model_dump(mode="json"))
        self.assertNotIn(VALUE, data)
        self.assertNotIn("encrypted", data.lower())

    def test_can_delete_is_the_users(self):
        self.assertEqual(
            SecretApiSecret.from_model(self.secret, self.admin_user).can_delete,
            user_can_delete(self.secret, "Secret", self.admin_user),
        )
        self.assertIs(SecretApiSecret.from_model(self.secret, self.non_admin_user).can_delete, False)
