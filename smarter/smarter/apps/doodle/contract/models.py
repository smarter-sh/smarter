"""
The response of the doodle of the day, ``GET /api/v1/doodles/today/``.

The sign-in page's React app, ``@smarter/doodle``, reads it. Its fields are camelCase.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from smarter.lib.typing import SmarterDictType


class DoodleApiModel(BaseModel):
    """The base class of the doodle api's models: camelCase JSON, and no undeclared fields."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    def to_json(self) -> SmarterDictType:
        """The model as the api returns it."""
        return self.model_dump(mode="json")


class DoodleOfTheDay(DoodleApiModel):
    """The doodle of a day in a region, as it is planned, before the switches apply."""

    date: str = Field(description="The visitor's local date, e.g. 2026-11-08.")
    region: str = Field(description="The visitor's region, e.g. south-asia.")
    theme: str = Field(description="The theme's slug, e.g. diwali, or default.")
    title: str = Field(description="What the doodle celebrates, e.g. Diwali.")
    caption: str = Field(description="The caption below the artwork, e.g. Happy Diwali! Empty for none.")
    alt_text: str = Field(description="The artwork's description, for screen readers.")
    link_url: str = Field(description="Where the caption links to. Empty for nowhere.")
    image_url: str = Field(description="The artwork's url. It never changes, and may be cached forever.")
    is_default: bool = Field(description="Whether it is the plain default doodle, which celebrates nothing.")


class DoodleApiResponse(DoodleOfTheDay):
    """The response of ``GET /api/v1/doodles/today/``: the doodle, and how to show it."""

    animated: bool = Field(description="Whether the artwork is animated.")
    show_caption: bool = Field(description="Whether to show the caption below the artwork.")

    @classmethod
    def from_doodle(cls, doodle: DoodleOfTheDay, animated: bool, show_caption: bool) -> "DoodleApiResponse":
        """
        Build the response from a planned doodle and the switches.

        :param doodle: The doodle of the day.
        :param animated: Whether the artwork may be animated.
        :param show_caption: Whether the caption may be shown.
        :returns: The response.
        :rtype: DoodleApiResponse
        """
        image_url = doodle.image_url
        if not animated:
            image_url = with_query(image_url, "still=1")
        caption_shown = show_caption and bool(doodle.caption) and not doodle.is_default
        fields = doodle.model_dump(by_alias=False)
        fields["image_url"] = image_url
        response = cls(**fields, animated=animated, show_caption=caption_shown)
        return response


def with_query(url: str, query: Optional[str]) -> str:
    """
    Add a query to a url.

    :param url: The url.
    :param query: The query, e.g. ``still=1``.
    :returns: The url with the query.
    :rtype: str
    """
    if not query:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{query}"


__all__ = ["DoodleApiResponse", "DoodleOfTheDay"]
