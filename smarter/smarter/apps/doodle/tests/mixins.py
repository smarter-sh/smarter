"""Fixtures of the doodle app's tests."""

import datetime

from smarter.apps.doodle.models import Doodle, DoodleArtwork, DoodleTheme
from smarter.apps.doodle.themes import load_themes
from smarter.lib.unittest.base_classes import SmarterTestBase

# The tests share the database with the dev platform, whose planner writes the doodles of the next
# week. Their days are years ahead, so that they never touch the dev platform's doodles.
DIWALI = datetime.date(2035, 10, 30)
"""Diwali in 2035, from the holidays package, which dates India's holidays up to 2035."""

QUIET_DAY = datetime.date(2035, 11, 3)
"""A day on which no theme of the catalog is due."""


class DoodleTestMixin(SmarterTestBase):
    """
    Load the real theme catalog once for the class, and delete what the class created.

    Tests share the database without a rollback, so the rows that existed before the class are
    remembered, and only the others are deleted afterwards.
    """

    themes: list[DoodleTheme]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.existing_doodles = set(Doodle.objects.values_list("id", flat=True))
        cls.existing_themes = set(DoodleTheme.objects.values_list("id", flat=True))
        cls.existing_artworks = set(DoodleArtwork.objects.values_list("id", flat=True))
        cls.themes = load_themes()

    @classmethod
    def tearDownClass(cls):
        Doodle.objects.exclude(id__in=cls.existing_doodles).delete()
        DoodleTheme.objects.exclude(id__in=cls.existing_themes).delete()
        DoodleArtwork.objects.exclude(id__in=cls.existing_artworks).filter(
            themes__isnull=True, doodles__isnull=True
        ).delete()
        super().tearDownClass()

    @classmethod
    def theme(cls, slug: str) -> DoodleTheme:
        """
        Return a theme of the catalog.

        :param slug: The theme's slug.
        :returns: The theme.
        :rtype: DoodleTheme
        """
        return DoodleTheme.objects.get(slug=slug)

    def delete_doodles(self, date: datetime.date):
        """
        Delete the doodles of a day that this class created.

        :param date: The day.
        """
        Doodle.objects.filter(date=date).exclude(id__in=self.existing_doodles).delete()
