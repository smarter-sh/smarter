"""
Test :mod:`smarter.apps.guardrail.templatetags.react_guardrail_list`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.template import Context, Template

from smarter.apps.guardrail.templatetags import react_guardrail_list
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestReactGuardrailListTemplateTag(SmarterTestBase):
    """Test the React guardrail-list template tag."""

    def test_template(self):
        """Test that the tag returns the app's JS and CSS assets, in a template."""
        self.assertEqual(react_guardrail_list.templatetag_manager.app_name, "@smarter/guardrail-list")
        assets = react_guardrail_list.guardrail_list_react_assets()
        self.assertEqual(set(assets.keys()), {"js", "css"})
        template = Template(
            "{% load react_guardrail_list %}{% guardrail_list_react_assets as assets %}{{ assets.js|length }}"
        )
        self.assertEqual(template.render(Context({})), str(len(assets["js"])))
