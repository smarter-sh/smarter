# pylint: disable=wrong-import-position
"""Test Charge model."""

from smarter.apps.account.models import Charge, ChargeTypes
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

        resource_locator = self.provider.record_locator
        charge = Charge.objects.create(
            resource_locator=resource_locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        self.addCleanup(Charge.objects.filter(resource_locator=resource_locator).delete)

        charge = Charge.objects.get(pk=charge.pk)
        self.assertEqual(charge.resource_locator, resource_locator)
        self.assertEqual(charge.charge_type, ChargeTypes.PROMPT_COMPLETION.value)
        self.assertEqual(charge.prompt_tokens, 10)
        self.assertEqual(charge.completion_tokens, 20)
        self.assertEqual(charge.total_tokens, 30)

        charge.charge_type = ChargeTypes.PLUGIN.value
        charge.prompt_tokens = 15
        charge.completion_tokens = 25
        charge.total_tokens = 40
        charge.save()

        charge = Charge.objects.get(pk=charge.pk)
        self.assertEqual(charge.charge_type, ChargeTypes.PLUGIN.value)
        self.assertEqual(charge.prompt_tokens, 15)
        self.assertEqual(charge.completion_tokens, 25)
        self.assertEqual(charge.total_tokens, 40)

        charge.delete()
        self.assertFalse(Charge.objects.filter(pk=charge.pk).exists())
