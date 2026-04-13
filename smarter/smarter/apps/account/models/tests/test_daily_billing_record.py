# pylint: disable=wrong-import-position
"""Test DailyBillingRecord model."""

import datetime

# our stuff
import logging

from smarter.apps.account.models import CHARGE_TYPES, DailyBillingRecord
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)


class TestDailyBillingRecord(TestAccountMixin):
    """Test DailyBillingRecord model"""

    logger_prefix = formatted_text(f"{__name__}.TestDailyBillingRecord()")

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

        DailyBillingRecord.objects.create(
            account=self.account,
            user=self.admin_user,
            provider="test-provider",
            date=datetime.date(2024, 1, 1),
            charge_type=CHARGE_TYPES[0][0],
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

        record = DailyBillingRecord.objects.get(account=self.account, user=self.admin_user, provider="test-provider")
        self.assertEqual(record.provider, "test-provider")
        self.assertEqual(record.charge_type, CHARGE_TYPES[0][0])
        self.assertEqual(record.prompt_tokens, 10)
        self.assertEqual(record.completion_tokens, 20)
        self.assertEqual(record.total_tokens, 30)

        record.provider = "updated-provider"
        record.prompt_tokens = 15
        record.completion_tokens = 25
        record.total_tokens = 40
        record.charge_type = CHARGE_TYPES[1][0]
        record.save()

        self.assertEqual(record.provider, "updated-provider")
        self.assertEqual(record.charge_type, CHARGE_TYPES[1][0])
        self.assertEqual(record.prompt_tokens, 15)
        self.assertEqual(record.completion_tokens, 25)
        self.assertEqual(record.total_tokens, 40)

        record.delete()
