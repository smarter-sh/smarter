# pylint: disable=wrong-import-position
"""Test Charge model."""

# our stuff
import logging

from smarter.apps.account.models import CHARGE_TYPES, Charge
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestCharge(TestAccountMixin):
    """Test Charge model"""

    logger_prefix = formatted_text(f"{__name__}.TestCharge()")

    @classmethod
    def setUpClass(cls):
        cls.provider = Provider.objects.create(name="Test Provider", slug="test-provider")
        super().setUpClass()
        logger.debug("%s Created provider: %s", cls.logger_prefix, cls.provider)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.provider.delete()
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s Error deleting provider: %s", cls.logger_prefix, e)

        super().tearDownClass()
        logger.debug("%s Tear down complete.", cls.logger_prefix)

    def test_crud(self):
        """
        Test that we can do all crud operations.
        """

        Charge.objects.create(
            account=self.account,
            user=self.admin_user,
            session_key="test_session_key",
            provider=self.provider,
            charge_type=CHARGE_TYPES[0][0],
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            model="test_model",
            reference="test_reference",
        )

        charge = Charge.objects.get(account=self.account, user=self.admin_user, session_key="test_session_key")
        self.assertEqual(charge.provider, self.provider)
        self.assertEqual(charge.charge_type, CHARGE_TYPES[0][0])
        self.assertEqual(charge.prompt_tokens, 10)
        self.assertEqual(charge.completion_tokens, 20)
        self.assertEqual(charge.total_tokens, 30)
        self.assertEqual(charge.model, "test_model")
        self.assertEqual(charge.reference, "test_reference")

        charge.session_key = "updated_session_key"
        charge.charge_type = CHARGE_TYPES[1][0]
        charge.prompt_tokens = 15
        charge.completion_tokens = 25
        charge.total_tokens = 40
        charge.model = "updated_test_model"
        charge.reference = "updated_reference"
        charge.save()

        self.assertEqual(charge.session_key, "updated_session_key")
        self.assertEqual(charge.charge_type, CHARGE_TYPES[1][0])
        self.assertEqual(charge.prompt_tokens, 15)
        self.assertEqual(charge.completion_tokens, 25)
        self.assertEqual(charge.total_tokens, 40)
        self.assertEqual(charge.model, "updated_test_model")
        self.assertEqual(charge.reference, "updated_reference")

        charge.delete()
