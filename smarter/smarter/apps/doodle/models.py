"""
Models of the doodle app.

- :class:`DoodleArtwork` is an SVG, stored once and named by its hash, so that its url never
  changes and a browser may cache it forever.
- :class:`DoodleTheme` is a theme of the catalog, ``data/themes/``: when it is due, where, its
  caption and its artwork. ``manage.py load_doodle_themes`` keeps the table in step with the files.
- :class:`Doodle` is the planned doodle of one day in one region, which the planner writes a week
  ahead, and which a superuser can override in the admin.
"""

from typing import Optional

from django.db import models

from smarter.lib.django.models import TimestampedModel

from .artwork import svg_sha256
from .regions import DoodleRegion
from .schedule import DoodleSchedule


class DoodleArtwork(TimestampedModel):
    """An SVG of a doodle, named by its content's SHA-256."""

    sha256 = models.CharField(max_length=64, unique=True, help_text="The SHA-256 of the SVG, in hex.")
    svg = models.TextField(help_text="The SVG.")

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Doodle Artwork"
        verbose_name_plural = "Doodle Artworks"

    def __str__(self) -> str:
        sha256 = str(self.sha256)
        return sha256[:12]

    @classmethod
    def for_svg(cls, svg: str) -> "DoodleArtwork":
        """
        Return the artwork of an SVG, stored once.

        :param svg: The SVG.
        :returns: The artwork, existing or new.
        :rtype: DoodleArtwork
        """
        sha256 = svg_sha256(svg)
        artwork, _ = cls.objects.get_or_create(sha256=sha256, defaults={"svg": svg})
        return artwork


class DoodleCategory(models.TextChoices):
    """What a theme celebrates.

    The planner's guardrails accept only these categories.
    """

    EVERGREEN = "evergreen", "Evergreen"
    CELEBRATION = "celebration", "Celebration"
    NATIONAL = "national", "National day"
    OBSERVANCE = "observance", "Day of recognition"
    SCIENCE = "science", "Science and computing"
    CULTURE = "culture", "Culture"
    SEASON = "season", "Season"
    SPORT = "sport", "Sport"


class DoodleTheme(TimestampedModel):
    """A theme of the catalog.

    See ``data/themes/README.md``.
    """

    slug = models.SlugField(max_length=64, unique=True, help_text="The theme's name, and its file's.")
    name = models.CharField(max_length=128, help_text="What the theme celebrates, e.g. Diwali.")
    category = models.CharField(max_length=32, choices=DoodleCategory.choices)
    caption = models.CharField(max_length=128, blank=True, default="", help_text="e.g. Happy Diwali!")
    alt_text = models.CharField(max_length=255, help_text="The artwork's description, for screen readers.")
    link_url = models.URLField(blank=True, default="", help_text="Where the caption links to.")
    priority = models.PositiveSmallIntegerField(
        default=50, help_text="When several themes are due, the one of the highest priority wins."
    )
    regions = models.JSONField(default=list, help_text='The regions that see it, or ["*"] for all of them.')
    schedule = models.JSONField(default=dict, help_text="When it is due. See DoodleSchedule.")
    props_svg = models.TextField(blank=True, default="", help_text="The props, drawn on the base scene.")
    artwork = models.ForeignKey(
        DoodleArtwork, on_delete=models.PROTECT, related_name="themes", help_text="The props on the base scene."
    )
    is_active = models.BooleanField(default=True, help_text="Whether the planner may choose it.")

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Doodle Theme"
        verbose_name_plural = "Doodle Themes"
        ordering = ["slug"]

    def __str__(self) -> str:
        return str(self.slug)

    @property
    def doodle_schedule(self) -> DoodleSchedule:
        """
        The theme's schedule.

        :returns: The schedule, validated.
        :rtype: DoodleSchedule
        """
        return DoodleSchedule.model_validate(self.schedule)


class DoodleStatus(models.TextChoices):
    """Whether a planned doodle may be shown."""

    APPROVED = "approved", "Approved"
    PROPOSED = "proposed", "Proposed, awaiting approval"
    REJECTED = "rejected", "Rejected"


class DoodleSource(models.TextChoices):
    """Who chose a planned doodle."""

    CALENDAR = "calendar", "The calendar"
    DEFAULT = "default", "The default, nothing was due"
    HUMAN = "human", "A person, in the admin"


class Doodle(TimestampedModel):
    """The doodle of one day in one region."""

    date = models.DateField(help_text="The local date on which it is shown.")
    region = models.CharField(max_length=32, choices=DoodleRegion.choices)
    theme = models.ForeignKey(DoodleTheme, on_delete=models.CASCADE, related_name="doodles")
    artwork = models.ForeignKey(DoodleArtwork, on_delete=models.PROTECT, related_name="doodles")
    status = models.CharField(max_length=16, choices=DoodleStatus.choices, default=DoodleStatus.APPROVED)
    source = models.CharField(max_length=16, choices=DoodleSource.choices, default=DoodleSource.CALENDAR)
    title = models.CharField(max_length=128, help_text="What it celebrates, e.g. Diwali.")
    caption = models.CharField(max_length=128, blank=True, default="")
    alt_text = models.CharField(max_length=255)
    link_url = models.URLField(blank=True, default="")
    reason = models.TextField(blank=True, default="", help_text="Why it was chosen.")

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Doodle"
        verbose_name_plural = "Doodles"
        ordering = ["-date", "region"]
        constraints = [models.UniqueConstraint(fields=["date", "region"], name="doodle_unique_date_region")]

    def __str__(self) -> str:
        return f"{self.date} {self.region} {self.theme}"

    @classmethod
    def shown(cls, date, region: str) -> Optional["Doodle"]:
        """
        Return the approved doodle of a day in a region.

        :param date: The local date.
        :param region: The region.
        :returns: The doodle, or ``None`` if none is planned and approved.
        :rtype: Optional[Doodle]
        """
        doodles = cls.objects.filter(date=date, region=region, status=DoodleStatus.APPROVED)
        doodle = doodles.select_related("theme", "artwork").first()
        return doodle


__all__ = [
    "Doodle",
    "DoodleArtwork",
    "DoodleCategory",
    "DoodleSource",
    "DoodleStatus",
    "DoodleTheme",
]
