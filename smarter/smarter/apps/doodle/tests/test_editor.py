"""
Test :mod:`smarter.apps.doodle.editor`, the Smarter Doodle Editor and Artist.

The LLMClients' prompts are patched, so no LLM is called: each test answers as the editor or
the artist would, and the editor's guardrails are tested on what it may and may not choose.
"""

import contextlib
import datetime
import os
from unittest.mock import MagicMock, patch

from django.utils import timezone
from waffle.testutils import override_switch

from smarter.apps.doodle import editor
from smarter.apps.doodle.const import DEFAULT_THEME_SLUG, EDITOR_MAX_ATTEMPTS
from smarter.apps.doodle.editor import (
    DoodleEditorDecision,
    check_decision,
    edit_day,
    edit_days,
    editor_request,
    has_blocked_word,
    needs_editing,
    observances,
    parse_answer,
    regions_to_edit,
)
from smarter.apps.doodle.models import (
    Doodle,
    DoodleEditorRun,
    DoodleEditorRunStatus,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from smarter.apps.doodle.planner import plan_doodle
from smarter.apps.doodle.regions import DoodleRegion
from smarter.apps.doodle.trends import DoodleTrend
from smarter.apps.llmclient.prompting import SmarterLLMClientPromptError
from smarter.apps.prompt.contract.models import (
    PromptChatApiMessage,
    PromptChatApiPromptResult,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .mixins import DIWALI, QUIET_DAY, DoodleTestMixin

REVOLUTION_DAY = datetime.date(2035, 11, 19)
"""Mexico's Revolution Day in 2035, a holiday that the catalog has no theme for."""

REVOLUTION_DAY_ID = "MX:revolution-day"

TRENDING_DAY = datetime.date(2035, 11, 21)
"""A day with nothing due in Oceania, when a trend is."""

ECLIPSE = DoodleTrend(
    id="en:Solar_eclipse_of_November_21,_2035",
    title="Solar eclipse of November 21, 2035",
    description="total solar eclipse",
    views=90000,
    url="https://en.wikipedia.org/wiki/Solar_eclipse_of_November_21,_2035",
)

ECLIPSE_DECISION = {
    "region": "oceania",
    "choice": "trend",
    "id": ECLIPSE.id,
    "reason": "Everyone is watching the eclipse.",
    "category": "science",
    "caption": "Happy eclipse day!",
    "alt_text": "A black sun with a golden ring above a Smarter LLMClient.",
    "link_url": "https://en.wikipedia.org/wiki/Something_else",
    "subject": "A sun hidden by the moon, with a golden corona, and stars.",
}

EDITOR = SmarterWaffleSwitches.ENABLE_DOODLE_LLM_EDITOR
TRENDS = SmarterWaffleSwitches.ENABLE_DOODLE_TRENDS
ARTWORK = SmarterWaffleSwitches.ENABLE_DOODLE_LLM_ARTWORK
AUTO_APPROVE = SmarterWaffleSwitches.ENABLE_DOODLE_AUTO_APPROVE

with open(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "artist", "safe.svg"), encoding="utf-8"
) as svg_file:
    SAFE_SVG = svg_file.read()


def answer(text: str) -> PromptChatApiPromptResult:
    """A prompt's result, whose assistant answered with a text."""
    return PromptChatApiPromptResult(status=200, messages=[PromptChatApiMessage(role="assistant", content=text)])


def decisions(*items: dict) -> PromptChatApiPromptResult:
    """The editor's answer, with decisions."""
    return answer(json.dumps({"decisions": list(items)}))


REVOLUTION_DAY_DECISION = {
    "region": "mx",
    "choice": "observance",
    "id": REVOLUTION_DAY_ID,
    "reason": "A national day in Mexico.",
    "category": "national",
    "caption": "Happy Revolution Day!",
    "alt_text": "Paper flags hang above a Smarter LLMClient.",
    "link_url": "https://en.wikipedia.org/wiki/Mexican_Revolution",
    "subject": "Paper flags in green, white and red.",
}


class TestDoodleEditor(DoodleTestMixin):
    """The editor chooses among the candidates that it is given, and its answer is checked again."""

    def setUp(self):
        super().setUp()
        self.tone = None
        for day in (DIWALI, QUIET_DAY, REVOLUTION_DAY, TRENDING_DAY):
            self.addCleanup(self.delete_doodles, day)
            self.addCleanup(DoodleEditorRun.objects.filter(date=day).delete)
        self.addCleanup(DoodleTheme.objects.filter(is_generated=True, slug__startswith="ai-2035").delete)

    @contextlib.contextmanager
    def llm(self, *results, exists: bool = True):
        """Answer the editor's and the artist's prompts with results, in order."""
        llmclient = MagicMock(id=1) if exists else None
        with (
            patch.object(editor, "smarter_llmclient", return_value=llmclient),
            patch.object(editor, "smarter_admin_profile", return_value=MagicMock()),
            patch.object(editor, "single_use_api_key", return_value=contextlib.nullcontext("a-key")),
            patch.object(editor, "prompt_llmclient", side_effect=list(results)) as prompt,
            patch.object(editor, "tone_check", return_value=self.tone),
        ):
            yield prompt

    # the request
    # ---------------------------------------------------------------------------------------------

    def test_editor_request(self):
        request = editor_request(DIWALI, ["south-asia", "mx"], artwork_allowed=False)
        self.assertEqual(request.date, DIWALI.isoformat())
        south_asia = request.region("south-asia")
        self.assertEqual([theme.id for theme in south_asia.catalog], ["diwali"])
        self.assertEqual(south_asia.observances, [])
        self.assertEqual(request.region("mx").catalog, [])
        self.assertIsNone(request.region("europe"))

    def test_observances(self):
        found = observances(REVOLUTION_DAY, "mx")
        self.assertEqual([(o.id, o.name, o.countries) for o in found], [(REVOLUTION_DAY_ID, "Revolution Day", ["MX"])])
        self.assertEqual(observances(REVOLUTION_DAY, "global"), [])

    def test_observances_leave_out_blocked_holidays(self):
        with patch.object(editor, "holidays_on", return_value=["National Day of Mourning", "Flower Day"]):
            found = observances(QUIET_DAY, "ca")
        self.assertEqual([o.name for o in found], ["Flower Day"])

    def test_blocked_words(self):
        blocked = [
            "Armistice Day",
            "King's Birthday",
            "Day of Remembrance for the Victims",
            "National Genocde Day",
            "Day of Bereavement",
        ]
        for text in blocked:
            with self.subTest(text=text):
                self.assertTrue(has_blocked_word(text))
        for text in ["Edward's Award Day", "Revolution Day", "Flower Day", "Independence Day"]:
            with self.subTest(text=text):
                self.assertFalse(has_blocked_word(text))

    # the answer
    # ---------------------------------------------------------------------------------------------

    def test_parse_answer(self):
        fenced = '```json\n{"decisions": [{"region": "mx", "choice": "default", "extra": 1}]}\n```'
        self.assertEqual(parse_answer(fenced).decisions[0].region, "mx")
        for text in [None, "", "No.", '{"decisions": "none"}', "{not json}"]:
            with self.subTest(text=text):
                with self.assertRaises(SmarterValueError):
                    parse_answer(text)

    def test_check_decision(self):
        request = editor_request(REVOLUTION_DAY, ["mx", "south-asia"], artwork_allowed=True)
        diwali_request = editor_request(DIWALI, ["south-asia"], artwork_allowed=True)
        no_artwork = editor_request(REVOLUTION_DAY, ["mx"], artwork_allowed=False)
        good = DoodleEditorDecision(**REVOLUTION_DAY_DECISION)
        self.assertIsNone(check_decision(good, request))
        self.assertIsNone(check_decision(DoodleEditorDecision(region="mx", choice="default"), request))
        self.assertIsNone(
            check_decision(DoodleEditorDecision(region="south-asia", choice="catalog", id="diwali"), diwali_request)
        )

        refused = {
            "unknown region": (DoodleEditorDecision(region="europe", choice="default"), request),
            "not due": (DoodleEditorDecision(region="mx", choice="catalog", id="christmas"), request),
            "artwork off": (good, no_artwork),
            "invented": (good.model_copy(update={"id": "MX:election-day"}), request),
            "category": (good.model_copy(update={"category": "politics"}), request),
            "caption": (good.model_copy(update={"caption": "x" * 61}), request),
            "alt text": (good.model_copy(update={"alt_text": ""}), request),
            "subject": (good.model_copy(update={"subject": None}), request),
            "link": (good.model_copy(update={"link_url": "https://example.com/"}), request),
            "blocked": (good.model_copy(update={"subject": "A war memorial."}), request),
        }
        for case, (decision, case_request) in refused.items():
            with self.subTest(case=case):
                self.assertIsNotNone(check_decision(decision, case_request))

        catalog_first = DoodleEditorDecision(**{**REVOLUTION_DAY_DECISION, "region": "south-asia"})
        self.assertIn("catalog themes", check_decision(catalog_first, diwali_request))

    # a day
    # ---------------------------------------------------------------------------------------------

    def test_the_editor_chooses_catalog_themes_and_the_default(self):
        plan_doodle(DIWALI, "south-asia")
        result = decisions(
            {"region": "south-asia", "choice": "catalog", "id": "diwali", "reason": "Diwali."},
            {"region": "mx", "choice": "default", "reason": "Nothing fits."},
            {"region": "us", "choice": "catalog", "id": "christmas", "reason": "Wrong."},
        )
        with override_switch(ARTWORK, active=False), self.llm(result) as prompt:
            run = edit_day(DIWALI)
        prompt.assert_called_once()
        self.assertEqual(run.status, DoodleEditorRunStatus.SUCCEEDED)
        self.assertIn("us: christmas is not a catalog theme", run.error)
        self.assertEqual(run.request["date"], DIWALI.isoformat())

        diwali = Doodle.objects.get(date=DIWALI, region="south-asia")
        self.assertEqual(diwali.source, DoodleSource.LLM)
        self.assertEqual(diwali.ai_credit, "chosen")
        self.assertIn("Chosen by the Smarter Doodle Editor: Diwali.", diwali.reason)
        mexico = Doodle.objects.get(date=DIWALI, region="mx")
        self.assertEqual(mexico.theme.slug, DEFAULT_THEME_SLUG)
        self.assertEqual(mexico.ai_credit, "")
        self.assertFalse(Doodle.objects.filter(date=DIWALI, region="us").exists())

    def test_the_artist_draws_an_observance_for_approval(self):
        with override_switch(ARTWORK, active=True), override_switch(AUTO_APPROVE, active=False):
            with self.llm(decisions(REVOLUTION_DAY_DECISION), answer(f"Here:\n{SAFE_SVG}")) as prompt:
                run = edit_day(REVOLUTION_DAY)
        self.assertEqual(prompt.call_count, 2)
        artist_prompt = json.loads(prompt.call_args_list[1].args[2])
        self.assertEqual(artist_prompt["name"], "Revolution Day")
        self.assertEqual(run.status, DoodleEditorRunStatus.SUCCEEDED)

        doodle = Doodle.objects.get(date=REVOLUTION_DAY, region="mx")
        self.assertEqual(doodle.status, DoodleStatus.PROPOSED)
        self.assertEqual(doodle.ai_credit, "drawn")
        self.assertEqual(doodle.caption, "Happy Revolution Day!")
        theme = doodle.theme
        self.assertTrue(theme.slug.startswith("ai-2035-11-19-mx-revolution-day-"))
        self.assertEqual(len(theme.slug), len("ai-2035-11-19-mx-revolution-day-") + 8)
        self.assertTrue(theme.is_generated)
        self.assertFalse(theme.is_active)
        self.assertIn("ai-sway", theme.artwork.svg)
        self.assertIn('id="doodle-base"', theme.artwork.svg)

    def test_a_drawn_observance_is_shown_at_once_with_auto_approve(self):
        with override_switch(ARTWORK, active=True), override_switch(AUTO_APPROVE, active=True):
            with self.llm(decisions(REVOLUTION_DAY_DECISION), answer(SAFE_SVG)):
                edit_day(REVOLUTION_DAY)
            # a second region that chooses the same observance reuses the drawing
            with self.llm(decisions({**REVOLUTION_DAY_DECISION})) as prompt:
                DoodleEditorRun.objects.filter(date=REVOLUTION_DAY).delete()
                edit_day(REVOLUTION_DAY)
        self.assertEqual(prompt.call_count, 1)
        doodle = Doodle.objects.get(date=REVOLUTION_DAY, region="mx")
        self.assertEqual(doodle.status, DoodleStatus.APPROVED)

    def test_the_calendar_stays_when_the_artist_fails(self):
        plan_doodle(REVOLUTION_DAY, "mx")
        failures = [answer("I can't draw that."), SmarterLLMClientPromptError("down")]
        for failure in failures:
            with self.subTest(failure=failure):
                DoodleEditorRun.objects.filter(date=REVOLUTION_DAY).delete()
                with override_switch(ARTWORK, active=True), patch.object(editor, "logger"):
                    with self.llm(decisions(REVOLUTION_DAY_DECISION), failure):
                        run = edit_day(REVOLUTION_DAY)
                self.assertEqual(run.status, DoodleEditorRunStatus.SUCCEEDED)
                doodle = Doodle.objects.get(date=REVOLUTION_DAY, region="mx")
                self.assertEqual(doodle.source, DoodleSource.DEFAULT)

    def test_the_artist_must_exist(self):
        decision = DoodleEditorDecision(**REVOLUTION_DAY_DECISION)
        observance = observances(REVOLUTION_DAY, "mx")[0]
        with patch.object(editor, "smarter_llmclient", return_value=None):
            with self.assertRaises(SmarterLLMClientPromptError):
                editor.draw(decision, observance, REVOLUTION_DAY)

    def test_a_failed_run_is_recorded_and_retried(self):
        with patch.object(editor, "logger"):
            for failure in [SmarterLLMClientPromptError("down"), answer("No.")]:
                with self.llm(failure):
                    run = edit_day(QUIET_DAY)
                self.assertEqual(run.status, DoodleEditorRunStatus.FAILED)
        self.assertTrue(needs_editing(QUIET_DAY))
        DoodleEditorRun.objects.create(date=QUIET_DAY, status=DoodleEditorRunStatus.FAILED, error="third")
        self.assertEqual(EDITOR_MAX_ATTEMPTS, 3)
        self.assertFalse(needs_editing(QUIET_DAY))

    def test_a_day_is_edited_once(self):
        DoodleEditorRun.objects.create(date=QUIET_DAY, status=DoodleEditorRunStatus.SUCCEEDED)
        self.assertFalse(needs_editing(QUIET_DAY))

    def test_regions_that_a_person_chose_are_left_alone(self):
        doodle = plan_doodle(QUIET_DAY, "ca")
        Doodle.objects.filter(pk=doodle.pk).update(source=DoodleSource.HUMAN)
        regions = regions_to_edit(QUIET_DAY)
        self.assertNotIn("ca", regions)
        self.assertEqual(len(regions), len(DoodleRegion.values) - 1)

    def test_without_the_editor(self):
        with self.llm(exists=False) as prompt, patch.object(editor, "logger"):
            self.assertIsNone(edit_day(QUIET_DAY))
            with override_switch(EDITOR, active=True):
                self.assertEqual(edit_days([QUIET_DAY]), 0)
        prompt.assert_not_called()

    def test_edit_days(self):
        result = decisions({"region": "global", "choice": "default", "reason": "Quiet."})
        with override_switch(EDITOR, active=False):
            self.assertEqual(edit_days([QUIET_DAY]), 0)
        with override_switch(EDITOR, active=True), override_switch(ARTWORK, active=False):
            with self.llm(result):
                self.assertEqual(edit_days([QUIET_DAY, QUIET_DAY]), 1)

    def test_smarter_llmclient_and_admin(self):
        self.assertIsNone(editor.smarter_llmclient("test_no_such_llmclient"))
        profile = editor.smarter_admin_profile()
        self.assertTrue(profile.user.is_staff)

    # trends: the editor's second look at a day, and the tone check of what it would draw
    # ---------------------------------------------------------------------------------------------

    def test_trends_are_due(self):
        today = timezone.now().date()
        with override_switch(TRENDS, active=True), override_switch(ARTWORK, active=True):
            self.assertTrue(editor.trends_are_due(today))
            self.assertTrue(editor.trends_are_due(today + datetime.timedelta(days=1)))
            self.assertFalse(editor.trends_are_due(today + datetime.timedelta(days=2)))
        with override_switch(TRENDS, active=False):
            self.assertFalse(editor.trends_are_due(today))
        with override_switch(TRENDS, active=True), override_switch(ARTWORK, active=False):
            self.assertFalse(editor.trends_are_due(today))

    def test_trends_bring_a_second_look(self):
        DoodleEditorRun.objects.create(date=TRENDING_DAY, status=DoodleEditorRunStatus.SUCCEEDED)
        with patch.object(editor, "trends_are_due", return_value=False):
            self.assertFalse(needs_editing(TRENDING_DAY))
        with patch.object(editor, "trends_are_due", return_value=True):
            self.assertTrue(needs_editing(TRENDING_DAY))
            DoodleEditorRun.objects.create(date=TRENDING_DAY, status=DoodleEditorRunStatus.SUCCEEDED, with_trends=True)
            self.assertFalse(needs_editing(TRENDING_DAY))

    def test_trend_drawn_with_its_own_link(self):
        with (
            patch.object(editor, "trends_are_due", return_value=True),
            patch.object(editor, "region_trends", return_value=[ECLIPSE]),
            override_switch(ARTWORK, active=True),
            override_switch(AUTO_APPROVE, active=False),
        ):
            with self.llm(decisions(ECLIPSE_DECISION), answer(SAFE_SVG)) as prompt:
                run = edit_day(TRENDING_DAY)
        self.assertTrue(run.with_trends)
        editor_prompt = json.loads(prompt.call_args_list[0].args[2])
        oceania = [region for region in editor_prompt["regions"] if region["region"] == "oceania"][0]
        self.assertEqual(oceania["trends"][0]["id"], ECLIPSE.id)
        doodle = Doodle.objects.get(date=TRENDING_DAY, region="oceania")
        self.assertEqual(doodle.status, DoodleStatus.PROPOSED)
        self.assertEqual(doodle.ai_credit, "drawn")
        self.assertEqual(doodle.link_url, ECLIPSE.url)
        self.assertEqual(doodle.title, ECLIPSE.title)

    def test_trend_that_is_not_in_the_request(self):
        request = editor_request(TRENDING_DAY, ["oceania"], artwork_allowed=True)
        decision = DoodleEditorDecision(**ECLIPSE_DECISION)
        self.assertIn("is not a trend", check_decision(decision, request))

    def test_trend_second_look_keeps_drawn_doodles(self):
        with override_switch(ARTWORK, active=True), override_switch(AUTO_APPROVE, active=True):
            with self.llm(decisions(REVOLUTION_DAY_DECISION), answer(SAFE_SVG)):
                edit_day(REVOLUTION_DAY)
        self.assertNotIn("mx", regions_to_edit(REVOLUTION_DAY, with_trends=True))
        self.assertIn("mx", regions_to_edit(REVOLUTION_DAY, with_trends=False))

    def test_tone_declines_what_is_not_upbeat(self):
        self.tone = "'Revolution Day' isn't upbeat enough for a doodle"
        with override_switch(ARTWORK, active=True), self.llm(decisions(REVOLUTION_DAY_DECISION)) as prompt:
            run = edit_day(REVOLUTION_DAY)
        prompt.assert_called_once()
        self.assertIn("isn't upbeat", run.error)
        self.assertFalse(Doodle.objects.filter(date=REVOLUTION_DAY, region="mx", source=DoodleSource.LLM).exists())

    def test_tone_check(self):
        decision = DoodleEditorDecision(**ECLIPSE_DECISION)
        subject = editor.DoodleEditorSubject(id=ECLIPSE.id, name=ECLIPSE.title, description="eclipse", link_url="")
        guardrails = patch.object(editor.Guardrail, "get_cached_object")
        with guardrails as lookup:
            lookup.side_effect = editor.Guardrail.DoesNotExist
            self.assertIn("doesn't exist", editor.tone_check(decision, subject))
        cases = [
            (MagicMock(error=None, triggered=False), None),
            (MagicMock(error=None, triggered=True), "isn't upbeat"),
            (MagicMock(error="the provider failed"), "the tone check failed"),
        ]
        for result, expected in cases:
            with self.subTest(expected=expected):
                with guardrails as lookup, patch.object(editor, "evaluate_guardrail", return_value=result) as evaluate:
                    lookup.return_value = MagicMock()
                    refusal = editor.tone_check(decision, subject)
                if expected is None:
                    self.assertIsNone(refusal)
                else:
                    self.assertIn(expected, refusal)
                self.assertIn("Solar eclipse", evaluate.call_args.args[1])
