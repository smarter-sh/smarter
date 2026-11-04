"""
The theme catalog: ``data/themes/<slug>.yaml``, and the props of each, ``<slug>.svg``.

``manage.py load_doodle_themes``, which ``initialize_platform`` runs, calls :func:`load_themes`
to keep the :class:`~smarter.apps.doodle.models.DoodleTheme` table in step with the files. A
theme's artwork is composed again each time, so that a change to the base scene reaches every
theme. See ``data/themes/README.md`` for the file format.
"""

import os
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .artwork import compose_svg
from .const import THEMES_PATH
from .models import DoodleArtwork, DoodleCategory, DoodleTheme
from .regions import ALL_REGIONS, DoodleRegion
from .schedule import DoodleSchedule

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)


class DoodleThemeSpec(BaseModel):
    """A theme's file, ``data/themes/<slug>.yaml``."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9-]+$", max_length=64, description="The theme's name, and its file's.")
    name: str = Field(max_length=128, description="What the theme celebrates.")
    category: DoodleCategory = Field(description="What kind of day it is.")
    caption: str = Field(default="", max_length=128, description="The caption below the artwork.")
    alt_text: str = Field(min_length=1, max_length=255, description="The artwork's description.")
    link_url: str = Field(default="", description="Where the caption links to: a page about the day.")
    priority: int = Field(default=50, ge=0, le=100, description="Higher wins when several themes are due.")
    regions: list[str] = Field(min_length=1, description='The regions that see it, or ["*"].')
    schedule: DoodleSchedule = Field(description="When it is due.")
    props: Optional[str] = Field(default=None, description="The props' file, beside it. <slug>.svg by default.")

    @field_validator("regions")
    @classmethod
    def check_regions(cls, regions: list[str]) -> list[str]:
        """
        Check that each region is a :class:`DoodleRegion`, or ``*``.

        :param regions: The theme's regions.
        :returns: The regions.
        :raises ValueError: If one isn't a region.
        """
        for region in regions:
            if region == ALL_REGIONS:
                continue
            if region not in DoodleRegion.values:
                raise ValueError(f"{region} is not a region. The regions are {DoodleRegion.values}.")
        return regions

    @field_validator("link_url")
    @classmethod
    def check_link_url(cls, link_url: str) -> str:
        """
        Check that the link is https.

        :param link_url: The link.
        :returns: The link.
        :raises ValueError: If it isn't empty or https.
        """
        if link_url and not link_url.startswith("https://"):
            raise ValueError("link_url must be an https url.")
        return link_url


def theme_files(folder: str = THEMES_PATH) -> list[str]:
    """
    Return the catalog's theme files.

    :param folder: The catalog's folder.
    :returns: The paths of the ``.yaml`` files, sorted.
    :rtype: list[str]
    """
    paths = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".yaml"):
            paths.append(os.path.join(folder, name))
    return paths


def read_theme(path: str) -> tuple[DoodleThemeSpec, str]:
    """
    Read a theme's file and its props.

    :param path: The theme's ``.yaml`` file.
    :returns: The theme, and its props' SVG, empty if it has none.
    :rtype: tuple[DoodleThemeSpec, str]
    :raises pydantic.ValidationError: If the file isn't a valid theme.
    :raises ValueError: If the slug isn't the file's name, or the props file named doesn't exist.
    """
    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file)
    spec = DoodleThemeSpec.model_validate(data)

    folder = os.path.dirname(path)
    file_name = os.path.basename(path)
    if file_name != f"{spec.slug}.yaml":
        raise ValueError(f"{file_name} has the slug {spec.slug}. A theme's file is named <slug>.yaml.")

    props_name = spec.props
    if props_name is None:
        props_name = f"{spec.slug}.svg"
    props_path = os.path.join(folder, props_name)
    if not os.path.exists(props_path):
        if spec.props is not None:
            raise ValueError(f"{file_name} names the props {spec.props}, which doesn't exist.")
        return spec, ""
    with open(props_path, encoding="utf-8") as file:
        props_svg = file.read()
    return spec, props_svg


def save_theme(spec: DoodleThemeSpec, props_svg: str) -> DoodleTheme:
    """
    Create or update a theme from its file.

    :param spec: The theme.
    :param props_svg: Its props.
    :returns: The theme.
    :rtype: DoodleTheme
    :raises SmarterValueError: If the props aren't a valid SVG of the base scene's viewBox.
    """
    svg = compose_svg(props_svg, spec.alt_text)
    artwork = DoodleArtwork.for_svg(svg)
    schedule = spec.schedule.model_dump(exclude_none=True)
    theme, created = DoodleTheme.objects.update_or_create(
        slug=spec.slug,
        defaults={
            "name": spec.name,
            "category": spec.category,
            "caption": spec.caption,
            "alt_text": spec.alt_text,
            "link_url": spec.link_url,
            "priority": spec.priority,
            "regions": spec.regions,
            "schedule": schedule,
            "props_svg": props_svg,
            "artwork": artwork,
            "is_active": True,
        },
    )
    action = "created" if created else "updated"
    logger.debug("%s.save_theme() %s the doodle theme %s.", logger_prefix, action, spec.slug)
    return theme


def load_themes(folder: str = THEMES_PATH) -> list[DoodleTheme]:
    """
    Load every theme of the catalog, and deactivate the themes whose files were removed.

    A removed theme is deactivated, not deleted, so that the past doodles that show it keep it.

    :param folder: The catalog's folder.
    :returns: The themes loaded.
    :rtype: list[DoodleTheme]
    :raises pydantic.ValidationError: If a file isn't a valid theme. No theme is changed then.
    :raises SmarterValueError: If a theme's props aren't a valid SVG. No theme is changed then.
    """
    # read and compose every theme first, so that one invalid file changes nothing.
    read = []
    for path in theme_files(folder):
        spec, props_svg = read_theme(path)
        compose_svg(props_svg, spec.alt_text)
        read.append((spec, props_svg))

    themes = []
    for spec, props_svg in read:
        themes.append(save_theme(spec, props_svg))

    slugs = [theme.slug for theme in themes]
    retired = DoodleTheme.objects.filter(is_active=True).exclude(slug__in=slugs)
    retired_count = retired.update(is_active=False)
    logger.info(
        "%s.load_themes() loaded %s doodle themes, and deactivated %s.", logger_prefix, len(themes), retired_count
    )
    return themes


__all__ = ["DoodleThemeSpec", "load_themes", "read_theme", "save_theme", "theme_files"]
