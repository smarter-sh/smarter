"""Test :mod:`smarter.apps.prompt.templatetags.react_workbench`."""

from django.template import Context, Template

from smarter.apps.prompt.templatetags import react_workbench
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestReactWorkbenchTemplateTag(SmarterTestBase):
    """Test the Prompt Engineer's Workbench template tag."""

    def test_template(self):
        """Test that the tag returns the app's JS and CSS assets, in a template."""
        self.assertEqual(react_workbench.templatetag_manager.app_name, "@smarter/workbench")
        assets = react_workbench.workbench_react_assets()
        self.assertIsInstance(assets, ReactAppAssets)
        template = Template("{% load react_workbench %}{% workbench_react_assets as assets %}{{ assets.js|length }}")
        self.assertEqual(template.render(Context({})), str(len(assets.js)))
