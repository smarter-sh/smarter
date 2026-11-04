"""
Trend signals for the Smarter Doodle Editor: what each region is reading about.

The Wikimedia Foundation publishes, every day, the most viewed articles of each language edition
of Wikipedia (the `pageviews api <https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html>`__).
During a World Cup, the football articles lead the Spanish, Portuguese and French editions, so the
editions that a region reads (:data:`REGION_PROJECTS`) are a regional signal of what people are
paying attention to. It is free, official and anonymous.

Trends are the riskiest candidates of the editor: most of what people read about is a person, a
death, a crime or the news. So a trend reaches the editor only if:

- it is an article, not the main page or a special page;
- it has a Wikidata item, whose English label and description it is judged by, whatever the
  edition's language (one ``wbgetentities`` request for all of an edition's top articles);
- its title, English label and English description have none of the editor's
  :data:`~smarter.apps.doodle.editor.BLOCKED_WORDS`, by the same language matching;
- its description isn't a person's: no years of life, e.g. ``(1950–2026)``, and none of
  :data:`PERSON_WORDS`, e.g. ``actor`` or ``footballer``. A doodle never draws a person;
- its description names an occasion, one of :data:`OCCASION_WORDS`, e.g. ``tournament``,
  ``festival`` or ``eclipse``: an allowlist, since a blocklist can't keep up with the news.

The editor may choose a trend only when the region has no catalog theme that day, and the artist
always draws it, so a trend's doodle awaits a superuser's approval unless auto-approve is on.

The day's top articles are those of the day before, or, until the api has published it, a few
hours after midnight UTC, of the day before that.
"""

import datetime
import re
from functools import lru_cache
from typing import Optional

from cache_results import cache_results
from django.utils import timezone
from pydantic import BaseModel, ConfigDict, Field

from smarter.apps.llmtool.plugin.safe_http import SafeHttpError, fetch
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .regions import DoodleRegion

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

PAGEVIEWS_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{project}/all-access/{year}/{month}/{day}"
"""The most viewed articles of a Wikipedia edition on a day."""

WIKIDATA_URL = "https://www.wikidata.org/w/api.php"
"""The Wikidata api, whose ``wbgetentities`` gives the English label and description of articles."""

USER_AGENT = "SmarterDoodle/1.0 (https://smarter.sh; the sign-in page's doodle of the day)"
"""Wikimedia asks every api client to identify itself."""

TRENDS_CACHE_TIMEOUT = 60 * 60 * 12
"""Seconds that a day's top articles, and their Wikidata items, are cached."""

TOP_ARTICLES_SCANNED = 25
"""How many of an edition's top articles are considered."""

MAX_TRENDS_PER_REGION = 8
"""How many trends of a region the editor is told about, at most."""

REGION_PROJECTS: dict[str, tuple[str, ...]] = {
    DoodleRegion.GLOBAL: ("en.wikipedia.org",),
    DoodleRegion.US: ("en.wikipedia.org",),
    DoodleRegion.CA: ("en.wikipedia.org", "fr.wikipedia.org"),
    DoodleRegion.MX: ("es.wikipedia.org",),
    DoodleRegion.LATAM: ("es.wikipedia.org", "pt.wikipedia.org"),
    DoodleRegion.EUROPE: ("de.wikipedia.org", "fr.wikipedia.org", "it.wikipedia.org", "pl.wikipedia.org"),
    DoodleRegion.AFRICA: ("fr.wikipedia.org", "sw.wikipedia.org"),
    DoodleRegion.MIDDLE_EAST: ("ar.wikipedia.org", "tr.wikipedia.org"),
    DoodleRegion.SOUTH_ASIA: ("hi.wikipedia.org", "bn.wikipedia.org"),
    DoodleRegion.EAST_ASIA: ("ja.wikipedia.org", "ko.wikipedia.org", "zh.wikipedia.org"),
    DoodleRegion.SOUTHEAST_ASIA: ("id.wikipedia.org", "vi.wikipedia.org", "th.wikipedia.org"),
    DoodleRegion.OCEANIA: ("en.wikipedia.org",),
}
"""
The Wikipedia editions whose readers stand for each region.

English is read everywhere, so it stands only for the regions where it is the first language;
elsewhere the region's own languages do, e.g. Spanish and Portuguese for Latin America.
"""

SKIPPED_TITLES = re.compile(r"^(Main_Page$|-$|[^_:]+:[^_])")
"""
Pages that aren't articles: the main page, and pages of other namespaces in any language, e.g.

``Especial:Buscar`` or ``Wikipedia:Portada``. An article whose title has a colon has a space
after it, e.g. ``Star_Wars:_Andor``, so it is kept.
"""

CALENDAR_ARTICLE = re.compile(r"\b(day|week|month) of the year\b|\bcalendar year\b|\bleap year\b", re.I)
"""The description of an article about a date itself, e.g. ``November 2``: ``day of the year``."""

LIFE_YEARS = re.compile(r"\(\s*(born\s+)?\d{3,4}\s*[–—-]\s*(\d{3,4})?\s*\)|\bborn\b|\(\s*b\.\s*\d{4}", re.I)
"""A person's years of life in a description, e.g. ``(1950–2026)`` or ``(born 1990)``."""

PERSON_WORDS = (
    "actor",
    "actress",
    "singer",
    "rapper",
    "musician",
    "politician",
    "footballer",
    "player",
    "athlete",
    "driver",
    "racer",
    "cyclist",
    "boxer",
    "wrestler",
    "fighter",
    "golfer",
    "swimmer",
    "coach",
    "manager",
    "businessman",
    "businesswoman",
    "entrepreneur",
    "engineer",
    "journalist",
    "influencer",
    "youtuber",
    "streamer",
    "model",
    "writer",
    "author",
    "poet",
    "painter",
    "artist",
    "director",
    "producer",
    "screenwriter",
    "comedian",
    "presenter",
    "host",
    "chef",
    "scientist",
    "professor",
    "activist",
    "monarch",
    "person",
    "people",
)
"""Words of a description that say that an article is about a person, or people."""

OCCASION_WORDS = (
    "tournament",
    "championship",
    "cup",
    "olympics",
    "olympic games",
    "games",
    "grand prix",
    "marathon",
    "race",
    "season",
    "match",
    "final",
    "festival",
    "carnival",
    "parade",
    "fair",
    "celebration",
    "holiday",
    "observance",
    "day",
    "week",
    "eclipse",
    "meteor shower",
    "comet",
    "aurora",
    "supermoon",
    "solstice",
    "equinox",
    "space mission",
    "spaceflight",
    "launch",
    "expedition",
    "exhibition",
    "contest",
)
"""
Words of an English description of an occasion that a doodle may celebrate: a sports event, a.

festival, a sky event, a space mission. A trend's description must have one: most of what people
read about, e.g. a film, an app, a company or a crime, has none.
"""


class DoodleTrend(BaseModel):
    """A trending article of a region, as the editor is told about it."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="A stable id: the edition's language and the article's title, e.g. es:Copa_Mundial.")
    title: str = Field(description="The article's English label, from Wikidata.")
    description: str = Field(description="Its English Wikidata description, e.g. association football tournament.")
    views: int = Field(description="Its views on the day.")
    url: str = Field(description="The article's url, which a doodle of it links to.")


def pageviews_day(day: datetime.date) -> datetime.date:
    """
    Return the day whose top articles stand for a day: the day before, which is complete.

    :param day: The day of the doodle.
    :returns: The day before it, or yesterday, whichever is earlier.
    :rtype: datetime.date
    """
    yesterday = timezone.now().date() - datetime.timedelta(days=1)
    before = day - datetime.timedelta(days=1)
    return min(before, yesterday)


def get_json(url: str, params: Optional[dict[str, str]] = None) -> dict:
    """
    GET a Wikimedia api, safely.

    :param url: The api's url.
    :param params: Its query parameters.
    :returns: The response's JSON.
    :rtype: dict
    :raises SafeHttpError: If the request fails, or the response isn't JSON.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    response = fetch(url, headers=headers, params=params, max_bytes=2_000_000)
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as e:
        raise SafeHttpError(f"{url} didn't return JSON: {e}") from e
    return data


@cache_results(timeout=TRENDS_CACHE_TIMEOUT)
def top_articles(project: str, day: str) -> list[tuple[str, int]]:
    """
    Return the most viewed articles of a Wikipedia edition on a day.

    :param project: The edition, e.g. ``es.wikipedia.org``.
    :param day: The day, as an ISO date.
    :returns: Each article's title and views, most viewed first, at most
        :data:`TOP_ARTICLES_SCANNED`, without pages that aren't articles.
    :rtype: list[tuple[str, int]]
    :raises SafeHttpError: If the api fails. A failure isn't cached.
    """
    date = datetime.date.fromisoformat(day)
    url = PAGEVIEWS_URL.format(project=project, year=date.year, month=f"{date.month:02d}", day=f"{date.day:02d}")
    data = get_json(url)
    items = data.get("items") or [{}]
    articles = []
    for item in items[0].get("articles", []):
        title = str(item.get("article", ""))
        if SKIPPED_TITLES.match(title):
            continue
        articles.append((title, int(item.get("views", 0))))
        if len(articles) >= TOP_ARTICLES_SCANNED:
            break
    return articles


def latest_top_articles(project: str, day: datetime.date) -> list[tuple[str, int]]:
    """
    Return the top articles of a day, or of the day before if the day's aren't published yet.

    The pageviews api publishes a day a few hours after it ends, in UTC.

    :param project: The edition, e.g. ``es.wikipedia.org``.
    :param day: The latest day wanted.
    :returns: The top articles of that day, or of the day before.
    :rtype: list[tuple[str, int]]
    :raises SafeHttpError: If neither day is available.
    """
    try:
        return top_articles(project, day.isoformat())
    except SafeHttpError:
        before = day - datetime.timedelta(days=1)
        return top_articles(project, before.isoformat())


def wiki_site(project: str) -> str:
    """
    Return the Wikidata site id of a Wikipedia edition.

    :param project: e.g. ``es.wikipedia.org``.
    :returns: e.g. ``eswiki``.
    :rtype: str
    """
    language = project.split(".", 1)[0]
    return f"{language.replace('-', '_')}wiki"


@cache_results(timeout=TRENDS_CACHE_TIMEOUT)
def article_entities(project: str, titles: tuple[str, ...]) -> dict[str, tuple[str, str, str]]:
    """
    Return the English label, English description and url of articles, from their Wikidata items.

    :param project: The edition, e.g. ``es.wikipedia.org``.
    :param titles: The articles' titles, with underscores, at most 50.
    :returns: Each title's English label, English description and article url. A title without
        a Wikidata item, or without an English description, is left out.
    :rtype: dict[str, tuple[str, str, str]]
    :raises SafeHttpError: If the api fails. A failure isn't cached.
    """
    site = wiki_site(project)
    names = [title.replace("_", " ") for title in titles]
    params = {
        "action": "wbgetentities",
        "sites": site,
        "titles": "|".join(names),
        "props": "labels|descriptions|sitelinks/urls",
        "languages": "en",
        "sitefilter": site,
        "format": "json",
    }
    data = get_json(WIKIDATA_URL, params=params)
    found: dict[str, tuple[str, str, str]] = {}
    for entity in (data.get("entities") or {}).values():
        if "missing" in entity:
            continue
        sitelink = (entity.get("sitelinks") or {}).get(site) or {}
        title = str(sitelink.get("title", "")).replace(" ", "_")
        url = str(sitelink.get("url", ""))
        label = str(((entity.get("labels") or {}).get("en") or {}).get("value", ""))
        description = str(((entity.get("descriptions") or {}).get("en") or {}).get("value", ""))
        if not title or not url or not description:
            continue
        found[title] = (label or title.replace("_", " "), description, url)
    return found


@lru_cache(maxsize=4096)
def is_a_person(description: str) -> bool:
    """
    Whether an article's description says that it is about a person.

    It is a pure function of its text, which the regions that share an edition ask about again,
    so its answers are kept for the life of the process.

    :param description: e.g. ``American actor (born 1956)``.
    :returns: True if it has years of life, or one of :data:`PERSON_WORDS`.
    :rtype: bool
    """
    if LIFE_YEARS.search(description):
        return True
    lowered = description.lower()
    for word in PERSON_WORDS:
        if re.search(rf"\b{word}s?\b", lowered):
            return True
    return False


@lru_cache(maxsize=4096)
def is_an_occasion(description: str) -> bool:
    """
    Whether an article's description says that it is an occasion that a doodle may celebrate.

    :param description: e.g. ``international association football tournament``.
    :returns: True if it has one of :data:`OCCASION_WORDS`, as whole words.
    :rtype: bool
    """
    lowered = description.lower()
    for word in OCCASION_WORDS:
        if re.search(rf"\b{re.escape(word)}s?\b", lowered):
            return True
    return False


def region_trends(region: str, day: datetime.date, refuse) -> list[DoodleTrend]:
    """
    Return the trends of a region that a doodle may celebrate.

    :param region: The region.
    :param day: The day of the doodle.
    :param refuse: A function that says whether a text has a blocked word, e.g.
        :func:`~smarter.apps.doodle.editor.has_blocked_word`.
    :returns: At most :data:`MAX_TRENDS_PER_REGION` trends, most viewed first. Empty if the api fails.
    :rtype: list[DoodleTrend]
    """
    trends: list[DoodleTrend] = []
    for project in REGION_PROJECTS.get(region, ()):
        try:
            articles = latest_top_articles(project, pageviews_day(day))
            titles = tuple(title for title, _ in articles)
            entities = article_entities(project, titles) if titles else {}
        except SafeHttpError as e:
            logger.warning("%s.region_trends() the trends of %s failed: %s", logger_prefix, project, e)
            continue
        language = project.split(".", 1)[0]
        for title, views in articles:
            entity = entities.get(title)
            if entity is None:
                continue
            label, description, url = entity
            if is_a_person(description):
                continue
            if "wikimedia" in description.lower():
                continue
            if CALENDAR_ARTICLE.search(description):
                continue
            if not is_an_occasion(description):
                continue
            if refuse(title.replace("_", " ")) or refuse(label) or refuse(description):
                continue
            trend = DoodleTrend(id=f"{language}:{title}", title=label, description=description, views=views, url=url)
            trends.append(trend)
    trends.sort(key=lambda trend: -trend.views)
    # editions often read about the same thing: keep its most viewed article, once.
    unique: list[DoodleTrend] = []
    seen: set[str] = set()
    for trend in trends:
        key = trend.title.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(trend)
    return unique[:MAX_TRENDS_PER_REGION]


__all__ = [
    "DoodleTrend",
    "REGION_PROJECTS",
    "article_entities",
    "is_a_person",
    "is_an_occasion",
    "region_trends",
    "top_articles",
]
