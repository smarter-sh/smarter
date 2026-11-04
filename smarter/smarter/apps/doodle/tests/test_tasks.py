"""Test :mod:`smarter.apps.doodle.tasks`."""

from unittest.mock import patch

from smarter.apps.doodle import tasks
from smarter.apps.doodle.const import PLANNING_DAYS
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.workers.celerybeat import app as beat_app


class TestDoodleTasks(SmarterTestBase):
    """Celery Beat plans the doodles."""

    def test_plan_doodles(self):
        with (
            patch.object(tasks.planner, "plan_doodles", return_value=108) as plan,
            patch.object(tasks.editor, "edit_days", return_value=1) as edit,
        ):
            self.assertEqual(tasks.plan_doodles(), 108)
        plan.assert_called_once_with(days=PLANNING_DAYS)
        window = edit.call_args.args[0]
        self.assertEqual(len(window), PLANNING_DAYS + 2)

    def test_beat_runs_it(self):
        entry = beat_app.conf.beat_schedule["plan-doodles"]
        self.assertEqual(entry["task"], "smarter.apps.doodle.tasks.plan_doodles")
        self.assertEqual(entry["task"], tasks.plan_doodles.name)
