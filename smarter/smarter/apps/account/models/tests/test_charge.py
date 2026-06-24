# pylint: disable=wrong-import-position
"""Test Charge model."""

from smarter.apps.account.models import CHARGE_TYPES, Charge
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider

# our stuff
from smarter.lib import logging

logger = logging.getLogger(__name__)


class TestCharge(TestAccountMixin):
    """Test Charge model."""

    logger_prefix = logging.formatted_text(f"{__name__}.TestCharge()")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = Provider.objects.create(name="Test Provider", user_profile=cls.user_profile)
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
        """Test that we can do all crud operations."""

        Charge.objects.create(
            charge_type=CHARGE_TYPES[0][0],
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

        charge = Charge.objects.get(user_profile=self.user_profile, session_key="test_session_key")
        self.assertEqual(charge.charge_type, CHARGE_TYPES[0][0])
        self.assertEqual(charge.prompt_tokens, 10)
        self.assertEqual(charge.completion_tokens, 20)
        self.assertEqual(charge.total_tokens, 30)

        charge.charge_type = CHARGE_TYPES[1][0]
        charge.prompt_tokens = 15
        charge.completion_tokens = 25
        charge.total_tokens = 40
        charge.save()

        self.assertEqual(charge.charge_type, CHARGE_TYPES[1][0])
        self.assertEqual(charge.prompt_tokens, 15)
        self.assertEqual(charge.completion_tokens, 25)
        self.assertEqual(charge.total_tokens, 40)

        charge.delete()
