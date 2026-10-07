"""
Test :mod:`smarter.apps.mcpclient.templatetags.react_mcpclient_list`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.template import Context, Template

from smarter.apps.mcpclient.templatetags import react_mcpclient_list
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestReactMCPClientListTemplateTag(SmarterTestBase):
    """Test the React mcpclient-list template tag."""

    def tag_name(self) -> str:
        """Return the name of the module's only template tag."""
        self.assertEqual(len(react_mcpclient_list.register.tags), 1)
        return next(iter(react_mcpclient_list.register.tags))

    def test_manager(self):
        """Test that the module's manager belongs to the mcpclient-list React app."""
        manager = react_mcpclient_list.templatetag_manager
        self.assertIsInstance(manager, SmarterReactTemplateTagManager)
        self.assertEqual(manager.app_name, "@smarter/mcpclient-list")

    def test_template(self):
        """Test that the tag returns the app's JS and CSS assets, in a template."""
        name = self.tag_name()
        template = Template(f"{{% load react_mcpclient_list %}}{{% {name} as assets %}}{{{{ assets.js|length }}}}")
        assets = react_mcpclient_list.templatetag_manager.reactapp_build_assets
        self.assertEqual(set(assets.keys()), {"js", "css"})
        self.assertEqual(template.render(Context({})), str(len(assets["js"])))
