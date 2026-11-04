"""
The Smarter Doodle Editor and Artist: two LLMClients that choose and draw the doodle of the day.

After the calendar has planned a day (:mod:`smarter.apps.doodle.planner`), the planner asks the
editor, the staff-only LLMClient ``smarter_doodle_editor`` of the Smarter account, to choose each
region's doodle of that day. The editor may only choose among what it is given:

- the region's **catalog** themes that are due, whose artwork exists and was reviewed;
- the region's **observances**: its other holidays that day, from the ``holidays`` package, which
  have no artwork yet. When it chooses one, the artist, ``smarter_doodle_artist``, draws it;
- the region's **trends**: what it is reading about on Wikipedia (:mod:`smarter.apps.doodle.trends`),
  on the editor's second look at today and tomorrow. The artist draws them too;
- the **default**: the plain scene.

Its answer is checked again here, whatever its system prompt says: a choice must be one of the
region's candidates; an observance or a trend must not be about mourning, war, politics or a
religion's holy day (:data:`BLOCKED_WORDS`), its category, caption and link must be fit to show, and
the ``upbeat_occasion_input`` Guardrail, a small LLM, must judge it fun and upbeat
(:func:`tone_check`). A choice that
fails is ignored, and the calendar's doodle stays. A drawn doodle is proposed, and a superuser
approves it in the admin, unless the ``enable_doodle_auto_approve`` switch is on.

Every prompt is recorded as a :class:`~smarter.apps.doodle.models.DoodleEditorRun`. A day is asked
once, or until it has failed :data:`~smarter.apps.doodle.const.EDITOR_MAX_ATTEMPTS` times.
"""

import datetime
import hashlib
import re
from functools import lru_cache
from typing import Literal, Optional

from django.utils import timezone
from django.utils.text import slugify
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.guardrail.api.v1.views.views import evaluate as evaluate_guardrail
from smarter.apps.guardrail.models import Guardrail, GuardrailStage
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.prompting import (
    SmarterLLMClientPromptError,
    assistant_text,
    prompt_llmclient,
    single_use_api_key,
)
from smarter.apps.llmtool.nlp import (
    simple_search,
    thesaurus_match,
    within_levenshtein_distance,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

from .artwork import compose_svg
from .const import (
    ARTIST_LLMCLIENT,
    DEFAULT_THEME_SLUG,
    EDITOR_LLMCLIENT,
    EDITOR_MAX_ATTEMPTS,
    MAX_OBSERVANCES_PER_REGION,
    TONE_GUARDRAIL,
    TRENDS_HORIZON_DAYS,
)
from .models import (
    Doodle,
    DoodleArtwork,
    DoodleCategory,
    DoodleEditorRun,
    DoodleEditorRunStatus,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from .planner import candidates, due_on, themes_without_svg
from .regions import DoodleRegion, region_countries
from .sanitize import extract_svg, sanitize_svg
from .schedule import DoodleSchedule, holidays_on
from .trends import DoodleTrend, region_trends

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.DOODLE_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

BLOCKED_WORDS = (
    "mourning",
    "memorial",
    "remembrance",
    "martyr",
    "massacre",
    "genocide",
    "victims",
    "tragedy",
    "disaster",
    "war",
    "armistice",
    "death",
    "funeral",
    "election",
    "referendum",
    "party",
    "president",
    "king",
    "queen",
    "prophet",
    "saint",
    "holy",
    "lent",
    "good friday",
    "ashura",
    "religious",
    "christian",
    "church",
    "feast day",
    "accident",
    "collision",
    "crash",
    "derailment",
    "killed",
    "attack",
    "shooting",
    "bombing",
    "explosion",
    "murder",
    "crime",
    "terrorism",
    "earthquake",
    "flood",
    "hurricane",
    "wildfire",
    "epidemic",
    "pandemic",
    "scandal",
    "protest",
    "riot",
    "trial",
)
"""
Words of a holiday that a doodle never celebrates on its own: mourning, war, politics, and a single.

religion's holy days. The catalog may still celebrate religious holidays that it chose, and drew,
with care, e.g. Diwali or Christmas. See :func:`has_blocked_word` for how a text matches one.
"""

OBSERVANCE_CATEGORIES = (
    DoodleCategory.CELEBRATION,
    DoodleCategory.NATIONAL,
    DoodleCategory.OBSERVANCE,
    DoodleCategory.SCIENCE,
    DoodleCategory.CULTURE,
    DoodleCategory.SEASON,
    DoodleCategory.SPORT,
)
"""The categories that a drawn observance may have."""

WIKIPEDIA = re.compile(r"^https://[a-z-]{2,12}\.wikipedia\.org/wiki/[^\s<>\"']+$")
"""The only links that a drawn doodle's caption may have: a Wikipedia article, of any edition."""


class DoodleEditorModel(BaseModel):
    """The base class of the editor's request and answer: snake_case JSON."""

    model_config = ConfigDict(extra="forbid")


class DoodleEditorCatalogTheme(DoodleEditorModel):
    """A catalog theme that is due in a region."""

    id: str = Field(description="The theme's slug.")
    name: str
    category: str
    priority: int


class DoodleEditorObservance(DoodleEditorModel):
    """A holiday of a region that the catalog has no theme for."""

    id: str = Field(description="A stable id, e.g. MX:revolution-day.")
    name: str = Field(description="The holiday's English name, from the holidays package.")
    countries: list[str] = Field(description="The countries of the region that observe it.")


class DoodleEditorRegion(DoodleEditorModel):
    """The candidates of one region."""

    region: str
    name: str
    catalog: list[DoodleEditorCatalogTheme]
    observances: list[DoodleEditorObservance]
    trends: list[DoodleTrend] = Field(
        default_factory=list, description="What the region is reading about, from Wikipedia. See trends.py."
    )


class DoodleEditorSubject(DoodleEditorModel):
    """What the artist draws: an observance or a trend that the editor chose."""

    id: str
    name: str
    description: str = Field(default="", description="What it is, e.g. a trend's Wikidata description.")
    link_url: str = Field(description="The page that the doodle's caption links to.")


class DoodleEditorRequest(DoodleEditorModel):
    """The editor's prompt: the day's candidates, in each region."""

    date: str
    artwork_allowed: bool
    regions: list[DoodleEditorRegion]

    def region(self, region: str) -> Optional[DoodleEditorRegion]:
        """
        Return the candidates of a region.

        :param region: The region.
        :returns: Its candidates, or ``None`` if the request doesn't have it.
        :rtype: Optional[DoodleEditorRegion]
        """
        for candidate in self.regions:
            if candidate.region == region:
                return candidate
        return None


class DoodleEditorDecision(BaseModel):
    """The editor's choice for one region.

    Extra fields are ignored: an LLM adds some.
    """

    model_config = ConfigDict(extra="ignore")

    region: str
    choice: Literal["catalog", "observance", "trend", "default"]
    id: Optional[str] = None
    reason: str = ""
    category: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    link_url: Optional[str] = None
    subject: Optional[str] = None


class DoodleEditorAnswer(BaseModel):
    """The editor's answer."""

    model_config = ConfigDict(extra="ignore")

    decisions: list[DoodleEditorDecision]


@lru_cache(maxsize=4096)
def has_blocked_word(text: str) -> bool:
    """
    Whether a text refers to one of the :data:`BLOCKED_WORDS`.

    It uses the plugin selectors' language matching, :mod:`smarter.apps.llmtool.nlp`: a whole word or
    its plural (``victims``), a typo of a longer word (``genocde``), or a synonym from the WordNet
    thesaurus (``bereavement`` for ``mourning``). A word never matches inside another, e.g. ``war``
    in ``Award``. It errs on the side of caution: a holiday that it blocks is simply not celebrated.
    It is a pure function of its text, and slow (each word is tried three ways), so its answers are
    kept for the life of the process: the regions that share a Wikipedia edition ask about the same
    texts again.

    :param text: e.g. a holiday's name, or the editor's caption.
    :returns: True if it refers to one.
    :rtype: bool
    """
    for word in BLOCKED_WORDS:
        if simple_search(text, word):
            return True
        if within_levenshtein_distance(text, word):
            return True
        if thesaurus_match(text, word) is not None:
            return True
    return False


def observances(day: datetime.date, region: str) -> list[DoodleEditorObservance]:
    """
    Return a region's holidays on a day, without those that a doodle never celebrates.

    :param day: The day.
    :param region: The region.
    :returns: At most :data:`~smarter.apps.doodle.const.MAX_OBSERVANCES_PER_REGION` holidays, each
        with the region's countries that observe it.
    :rtype: list[DoodleEditorObservance]
    """
    countries_of: dict[str, list[str]] = {}
    for country in region_countries(region):
        for name in holidays_on(country, day):
            if has_blocked_word(name):
                continue
            countries_of.setdefault(name, []).append(country)

    found = []
    for name, countries in sorted(countries_of.items()):
        observance_id = f"{countries[0]}:{slugify(name)}"
        found.append(DoodleEditorObservance(id=observance_id, name=name, countries=countries))
        if len(found) >= MAX_OBSERVANCES_PER_REGION:
            break
    return found


def editor_request(
    day: datetime.date, regions: list[str], artwork_allowed: bool, with_trends: bool = False
) -> DoodleEditorRequest:
    """
    Build the editor's prompt for a day.

    :param day: The day.
    :param regions: The regions to choose for.
    :param artwork_allowed: Whether the editor may choose a holiday that the artist must draw.
    :param with_trends: Whether to tell the editor what each region is reading about, which the
        artist must draw too. See :mod:`smarter.apps.doodle.trends`.
    :returns: The request.
    :rtype: DoodleEditorRequest
    """
    labels = dict(DoodleRegion.choices)
    due = due_on(day)
    request_regions = []
    for region in regions:
        catalog = []
        for theme in candidates(day, region, due=due):
            catalog.append(
                DoodleEditorCatalogTheme(
                    id=theme.slug, name=theme.name, category=theme.category, priority=theme.priority
                )
            )
        region_observances = []
        region_trends_ = []
        if artwork_allowed:
            region_observances = observances(day, region)
            if with_trends:
                region_trends_ = region_trends(region, day, has_blocked_word)
        label = str(labels[region])
        request_regions.append(
            DoodleEditorRegion(
                region=region,
                name=label,
                catalog=catalog,
                observances=region_observances,
                trends=region_trends_,
            )
        )
    return DoodleEditorRequest(date=day.isoformat(), artwork_allowed=artwork_allowed, regions=request_regions)


def parse_answer(text: Optional[str]) -> DoodleEditorAnswer:
    """
    Parse the editor's answer.

    :param text: The answer, which should be one JSON object, perhaps in a code fence.
    :returns: The decisions.
    :rtype: DoodleEditorAnswer
    :raises SmarterValueError: If it isn't a valid answer.
    """
    if not text:
        raise SmarterValueError("The editor gave no answer.")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end < start:
        raise SmarterValueError("The editor's answer has no JSON object.")
    try:
        data = json.loads(text[start : end + 1])
        answer = DoodleEditorAnswer.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise SmarterValueError(f"The editor's answer isn't valid: {e}") from e
    return answer


def check_decision(decision: DoodleEditorDecision, request: DoodleEditorRequest) -> Optional[str]:
    """
    Check a decision against the request and the guardrails.

    :param decision: A region's decision.
    :param request: The request it answers.
    :returns: Why the decision is refused, or ``None`` if it is fine.
    :rtype: Optional[str]
    """
    candidates_of_region = request.region(decision.region)
    if candidates_of_region is None:
        return f"the request has no region {decision.region}"
    if decision.choice == "default":
        return None
    if decision.choice == "catalog":
        catalog_ids = [theme.id for theme in candidates_of_region.catalog]
        if decision.id not in catalog_ids:
            return f"{decision.id} is not a catalog theme of {decision.region} that day"
        return None

    # an observance or a trend, which the artist must draw
    if not request.artwork_allowed:
        return "artwork isn't allowed"
    if candidates_of_region.catalog:
        return "the region has catalog themes, which come first"
    subject = drawable_subject(decision, request)
    if subject is None:
        return f"{decision.id} is not a {decision.choice} of {decision.region} that day"
    if decision.category not in OBSERVANCE_CATEGORIES:
        return f"the category {decision.category} isn't allowed"
    if not decision.caption or len(decision.caption) > 60:
        return "the caption is missing, or longer than 60 characters"
    if not decision.alt_text or len(decision.alt_text) > 255:
        return "the alt text is missing, or longer than 255 characters"
    if not decision.subject:
        return "the subject for the artist is missing"
    if subject.link_url and not WIKIPEDIA.match(subject.link_url):
        return f"the link {subject.link_url} isn't a Wikipedia article"
    for text in (subject.name, decision.caption, decision.subject, decision.alt_text):
        if has_blocked_word(text):
            return f"{text!r} is about a topic that a doodle never celebrates"
    return None


def drawable_subject(decision: DoodleEditorDecision, request: DoodleEditorRequest) -> Optional[DoodleEditorSubject]:
    """
    Return the observance or the trend that a decision chose, for the artist to draw.

    An observance's link is the one that the editor wrote, which is checked. A trend's is its own
    article's, whatever the editor wrote.

    :param decision: An ``observance`` or ``trend`` decision.
    :param request: The request it answers.
    :returns: The subject, or ``None`` if the region had no such candidate.
    :rtype: Optional[DoodleEditorSubject]
    """
    candidates_of_region = request.region(decision.region)
    if candidates_of_region is None:
        return None
    if decision.choice == "observance":
        for observance in candidates_of_region.observances:
            if observance.id == decision.id:
                countries = ", ".join(observance.countries)
                return DoodleEditorSubject(
                    id=observance.id,
                    name=observance.name,
                    description=f"a public holiday of {countries}",
                    link_url=decision.link_url or "",
                )
    if decision.choice == "trend":
        for trend in candidates_of_region.trends:
            if trend.id == decision.id:
                return DoodleEditorSubject(
                    id=trend.id, name=trend.title, description=trend.description, link_url=trend.url
                )
    return None


def tone_check(decision: DoodleEditorDecision, subject: DoodleEditorSubject) -> Optional[str]:
    """
    Ask the ``upbeat_occasion_input`` Guardrail whether an occasion is fun and upbeat.

    It is a tone check, by a small LLM, which the word lists can't do: a solemn anniversary or sad
    news has no blocked word. It fails closed: without the Guardrail, or when it fails, nothing
    is drawn.

    :param decision: The editor's decision, whose caption and subject are judged too.
    :param subject: The observance or trend.
    :returns: Why the occasion is declined, or ``None`` if it is upbeat.
    :rtype: Optional[str]
    """
    account = smarter_cached_objects.smarter_account
    try:
        guardrail: Guardrail = Guardrail.get_cached_object(name=TONE_GUARDRAIL, account=account)  # type: ignore[assignment]
    except Guardrail.DoesNotExist:
        return f"the Guardrail {TONE_GUARDRAIL} doesn't exist, so nothing is drawn"
    text = (
        f"{subject.name}: {subject.description}. "
        f"The caption: {decision.caption}. The illustration: {decision.subject}"
    )
    result = evaluate_guardrail(guardrail, text, GuardrailStage.INPUT)
    if result.error:
        return f"the tone check failed, so nothing is drawn: {result.error}"
    if result.triggered:
        return f"{subject.name!r} isn't upbeat enough for a doodle, says {TONE_GUARDRAIL}"
    return None


def smarter_llmclient(name: str) -> Optional[LLMClient]:
    """
    Return an LLMClient of the Smarter account, by name.

    :param name: e.g. :data:`~smarter.apps.doodle.const.EDITOR_LLMCLIENT`.
    :returns: The LLMClient, or ``None`` if the example manifests that declare it aren't loaded.
        A missing LLMClient isn't cached, so it is found as soon as they are.
    :rtype: Optional[LLMClient]
    """
    account = smarter_cached_objects.smarter_account
    try:
        llmclient = LLMClient.get_cached_object(name=name, account=account)
    except LLMClient.DoesNotExist:
        return None
    return llmclient


def smarter_admin_profile() -> UserProfile:
    """
    Return the user profile of the Smarter account's admin, who owns the doodle's LLMClients.

    :returns: The profile.
    :rtype: UserProfile
    """
    profile = smarter_cached_objects.smarter_admin_user_profile
    return profile


def draw(decision: DoodleEditorDecision, subject: DoodleEditorSubject, day: datetime.date) -> DoodleTheme:
    """
    Ask the artist to draw an observance or a trend, and save it as a theme of that day only.

    :param decision: The editor's decision.
    :param subject: The observance or trend.
    :param day: The day.
    :returns: The theme, inactive, so that the calendar never chooses it.
    :rtype: DoodleTheme
    :raises SmarterLLMClientPromptError: If the artist doesn't exist, or the prompt fails.
    :raises SmarterValueError: If its answer isn't a safe SVG of the base scene's viewBox.
    """
    # one theme per country's holiday, or edition's article: those of the same name have their own link.
    # The hash keeps apart the ids that slugify empties, e.g. the Hindi or Japanese titles of trends.
    readable = slugify(f"ai-{day.isoformat()}-{subject.id.replace(':', '-')}")[:54].rstrip("-")
    digest = hashlib.sha1(subject.id.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]
    slug = f"{readable}-{digest}"
    existing = themes_without_svg().filter(slug=slug).first()
    if existing is not None:
        return existing

    artist = smarter_llmclient(ARTIST_LLMCLIENT)
    if artist is None:
        raise SmarterLLMClientPromptError(f"The LLMClient {ARTIST_LLMCLIENT} doesn't exist.")
    prefix = "ai"
    prompt = json.dumps({"name": subject.name, "subject": decision.subject, "prefix": prefix})
    with single_use_api_key(smarter_admin_profile(), "doodle_artist") as token_key:
        result = prompt_llmclient(artist, token_key, prompt)
    answer = assistant_text(result) or ""
    props_svg = sanitize_svg(extract_svg(answer), prefix)
    alt_text = str(decision.alt_text)
    svg = compose_svg(props_svg, alt_text)
    artwork = DoodleArtwork.for_svg(svg)
    schedule = DoodleSchedule(kind="never").model_dump(exclude_none=True)
    theme = DoodleTheme.objects.create(
        slug=slug,
        name=subject.name[:128],
        category=str(decision.category),
        caption=str(decision.caption),
        alt_text=alt_text,
        link_url=subject.link_url,
        priority=0,
        regions=[decision.region],
        schedule=schedule,
        props_svg=props_svg,
        artwork=artwork,
        is_active=False,
        is_generated=True,
    )
    logger.info("%s.draw() the Smarter Doodle Artist drew %s for %s.", logger_prefix, subject.name, day)
    return theme


def apply_decision(
    decision: DoodleEditorDecision, request: DoodleEditorRequest, day: datetime.date
) -> Optional[Doodle]:
    """
    Apply a checked decision to its region's doodle of the day.

    :param decision: The decision, which :func:`check_decision` accepted.
    :param request: The request it answers.
    :param day: The day.
    :returns: The doodle, or ``None`` if the artist failed and the calendar's doodle stays.
    :rtype: Optional[Doodle]
    """
    status = DoodleStatus.APPROVED
    reason = f"Chosen by the Smarter Doodle Editor: {decision.reason}"
    if decision.choice in ("observance", "trend"):
        subject = drawable_subject(decision, request)
        try:
            theme = draw(decision, subject, day)  # type: ignore[arg-type]
        except (SmarterLLMClientPromptError, SmarterValueError) as e:
            logger.warning(
                "%s.apply_decision() the artist failed, so the calendar's doodle stays: %s", logger_prefix, e
            )
            return None
        if not switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_AUTO_APPROVE):
            status = DoodleStatus.PROPOSED
        reason = f"Chosen by the Smarter Doodle Editor, and drawn by the Smarter Doodle Artist: {decision.reason}"
    elif decision.choice == "catalog":
        theme = themes_without_svg().get(slug=decision.id)
    else:
        theme = themes_without_svg().get(slug=DEFAULT_THEME_SLUG)

    doodle, _ = Doodle.objects.update_or_create(
        date=day,
        region=decision.region,
        defaults={
            "theme": theme,
            "artwork": theme.artwork,
            "status": status,
            "source": DoodleSource.LLM,
            "title": theme.name,
            "caption": theme.caption,
            "alt_text": theme.alt_text,
            "link_url": theme.link_url,
            "reason": reason[:2000],
        },
    )
    return doodle


def regions_to_edit(day: datetime.date, with_trends: bool = False) -> list[str]:
    """
    Return the regions whose doodle of a day the editor may choose: not one that a person chose.

    :param day: The day.
    :param with_trends: Whether it is the editor's second look at the day, with trends. Then a
        doodle that the artist drew, which a superuser may have approved, is kept too.
    :returns: The regions.
    :rtype: list[str]
    """
    kept = set(Doodle.objects.filter(date=day, source=DoodleSource.HUMAN).values_list("region", flat=True))
    if with_trends:
        drawn = Doodle.objects.filter(date=day, theme__is_generated=True).values_list("region", flat=True)
        kept.update(drawn)
    regions = []
    for region in DoodleRegion.values:
        if region in kept:
            continue
        regions.append(region)
    return regions


def trends_are_due(day: datetime.date) -> bool:
    """
    Whether the editor looks at a day with trends: they are news, so only today's and tomorrow's.

    :param day: The day.
    :returns: True while the ``enable_doodle_trends`` and ``enable_doodle_llm_artwork`` switches are
        on, and the day is at most :data:`~smarter.apps.doodle.const.TRENDS_HORIZON_DAYS` after today.
    :rtype: bool
    """
    if not switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_TRENDS):
        return False
    if not switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_LLM_ARTWORK):
        return False
    today = timezone.now().date()
    horizon = today + datetime.timedelta(days=TRENDS_HORIZON_DAYS)
    return day <= horizon


def needs_editing(day: datetime.date) -> bool:
    """
    Whether the editor should be asked about a day.

    The editor looks at each day once, a week ahead, and once more, with trends, the day before.

    :param day: The day.
    :returns: False if a run of that day succeeded, with trends when they are due, or failed too
        many times.
    :rtype: bool
    """
    with_trends = trends_are_due(day)
    runs = DoodleEditorRun.objects.filter(date=day, with_trends=with_trends)
    if runs.filter(status=DoodleEditorRunStatus.SUCCEEDED).exists():
        return False
    failures = runs.filter(status=DoodleEditorRunStatus.FAILED).count()
    return failures < EDITOR_MAX_ATTEMPTS


def edit_day(day: datetime.date) -> Optional[DoodleEditorRun]:
    """
    Ask the editor to choose the doodles of a day, and apply its choices.

    :param day: The day, which the calendar has planned.
    :returns: The run, or ``None`` if the editor doesn't exist on this platform.
    :rtype: Optional[DoodleEditorRun]
    """
    editor = smarter_llmclient(EDITOR_LLMCLIENT)
    if editor is None:
        logger.info(
            "%s.edit_day() the LLMClient %s doesn't exist, so the calendar chooses the doodles.",
            logger_prefix,
            EDITOR_LLMCLIENT,
        )
        return None

    artwork_allowed = switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_LLM_ARTWORK)
    with_trends = trends_are_due(day)
    regions = regions_to_edit(day, with_trends=with_trends)
    request = editor_request(day, regions, artwork_allowed, with_trends=with_trends)
    request_json = request.model_dump(mode="json")
    run = DoodleEditorRun(date=day, request=request_json, with_trends=with_trends)

    try:
        with single_use_api_key(smarter_admin_profile(), "doodle_editor") as token_key:
            result = prompt_llmclient(editor, token_key, json.dumps(request_json))
        text = assistant_text(result)
        run.response = text or ""
        answer = parse_answer(text)
    except (SmarterLLMClientPromptError, SmarterValueError) as e:
        run.status = DoodleEditorRunStatus.FAILED
        run.error = str(e)
        run.save()
        logger.warning("%s.edit_day() the editor failed for %s: %s", logger_prefix, day, e)
        return run

    refused = []
    for decision in answer.decisions:
        refusal = check_decision(decision, request)
        if refusal is None and decision.choice in ("observance", "trend"):
            subject = drawable_subject(decision, request)
            refusal = tone_check(decision, subject)  # type: ignore[arg-type]
        if refusal is not None:
            refused.append(f"{decision.region}: {refusal}")
            continue
        apply_decision(decision, request, day)

    run.status = DoodleEditorRunStatus.SUCCEEDED
    run.error = "\n".join(refused)
    run.save()
    logger.info(
        "%s.edit_day() the editor chose the doodles of %s, and %s of its choices were refused.",
        logger_prefix,
        day,
        len(refused),
    )
    return run


def edit_days(days: list[datetime.date]) -> int:
    """
    Ask the editor about each day that needs it, while the ``enable_doodle_llm_editor`` switch is on.

    :param days: The planned days.
    :returns: The number of days that the editor was asked about.
    :rtype: int
    """
    if not switch_is_active(SmarterWaffleSwitches.ENABLE_DOODLE_LLM_EDITOR):
        return 0
    asked = 0
    for day in days:
        if not needs_editing(day):
            continue
        run = edit_day(day)
        if run is None:
            break
        asked += 1
    return asked


__all__ = [
    "BLOCKED_WORDS",
    "DoodleEditorAnswer",
    "DoodleEditorDecision",
    "DoodleEditorRequest",
    "check_decision",
    "edit_day",
    "edit_days",
    "editor_request",
    "observances",
    "parse_answer",
]
