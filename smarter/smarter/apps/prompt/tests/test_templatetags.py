"""Test :mod:`smarter.apps.prompt.templatetags.react_smarter_chat`."""

from django.template import Context, Template

from smarter.apps.prompt.templatetags import react_smarter_chat
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestReactSmarterChatTemplateTag(SmarterTestBase):
    """Test the Smarter Chat template tag."""

    def test_template(self):
        """Test that the tag returns the app's JS and CSS assets, in a template."""
        self.assertEqual(react_smarter_chat.templatetag_manager.app_name, "@smarter.sh/ui-chat")
        assets = react_smarter_chat.smarter_chat_react_assets()
        self.assertEqual(set(assets.keys()), {"js", "css"})
        template = Template(
            "{% load react_smarter_chat %}{% smarter_chat_react_assets as assets %}{{ assets.js|length }}"
        )
        self.assertEqual(template.render(Context({})), str(len(assets["js"])))
