"""
Test the verify_stackademy management command, :mod:`smarter.apps.llmclient.management.commands.verify_stackademy`.

The chat api that the command prompts is patched, so no LLM is called. ``SmarterCommand.handle_completed_failure()``
calls ``sys.exit(1)`` when it is given an exception, so a failure is asserted as ``SystemExit``.
The layout of the Stackademy manifests, which several apps' ``add_example_<kinds>`` commands apply,
is tested here too.
"""

import glob
import io
import os
from contextlib import redirect_stdout
from http import HTTPStatus
from unittest import mock

import yaml
from django.core.management import CommandError, call_command

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.demos.const import STACKADEMY_API_CONNECTION_NAME
from smarter.apps.api.v1.demos.urls import ApiV1DemoUrls
from smarter.apps.llmclient.management.commands import verify_stackademy
from smarter.apps.prompt.contract.models import PromptChatApiMessage
from smarter.common.const import PROJECT_ROOT
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.django.shortcuts import reverse
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.manifest.template import (
    manifest_template_values,
    render_manifest_template,
)
from smarter.lib.typing import SmarterDictType

MODULE = "smarter.apps.llmclient.management.commands.verify_stackademy"
UNKNOWN_ACCOUNT_NUMBER = "9999-9999-9999"
UNKNOWN_LLMCLIENT_NAME = "test_verify_stackademy_no_such_llmclient"
TOOL_CALL = {"role": "smarter", "content": "openai called this tool: a_plugin()"}
ANSWER = {"role": "assistant", "content": "Yes, we offer CS210, Artificial Intelligence."}
APPS = os.path.join(PROJECT_ROOT, "apps")


class TestStackademyManifests(TestAccountMixin):
    """Test that each Stackademy manifest is in the data/stackademy/ folder of the app that implements its kind."""

    KINDS = {
        "Secret": "secret",
        "Budget": "account",
        "SqlConnection": "connection",
        "ApiConnection": "connection",
        "SqlPlugin": "llmtool",
        "ApiPlugin": "llmtool",
        "LLMClient": "llmclient",
    }

    def manifests(self) -> dict[str, list[str]]:
        """The kinds of the manifests in every app's data/stackademy/ folder."""
        retval: dict[str, list[str]] = {}
        for filespec in glob.glob(os.path.join(APPS, "*", "data", "stackademy", "*")):
            with open(filespec, encoding="utf-8") as f:
                kind = next(line.split(":", 1)[1].strip() for line in f if line.startswith("kind:"))
            retval.setdefault(kind, []).append(filespec)
        return retval

    def test_each_manifest_is_in_its_kinds_app(self):
        manifests = self.manifests()
        self.assertEqual(set(manifests), set(self.KINDS))
        for kind, filespecs in manifests.items():
            for filespec in filespecs:
                with self.subTest(filespec=filespec):
                    self.assertTrue(filespec.startswith(os.path.join(APPS, self.KINDS[kind], "data", "stackademy")))

    def test_api_connection(self):
        """Test that the ApiConnection queries this platform's course catalogue, with its own Secret."""
        (filespec,) = self.manifests()["ApiConnection"]
        with open(filespec, encoding="utf-8") as f:
            connection = yaml.safe_load(render_manifest_template(f.read()))
        values = manifest_template_values()
        spec = connection["spec"]["connection"]
        self.assertEqual(connection["metadata"]["name"], STACKADEMY_API_CONNECTION_NAME)
        self.assertEqual(
            spec["baseUrl"], f"{values['environment_platform_scheme']}://{values['environment_platform_domain']}"
        )
        self.assertEqual(spec["authMethod"], "token")
        self.assertEqual(spec["apiKey"], "smarter_test_api")
        self.assertIn(
            "smarter_test_api", [get_readonly_yaml_file(f)["metadata"]["name"] for f in self.manifests()["Secret"]]
        )
        plugin = get_readonly_yaml_file(
            os.path.join(APPS, "llmtool", "data", "stackademy", "stackademy-plugin-api.yaml")
        )
        self.assertEqual(
            plugin["spec"]["apiData"]["endpoint"],
            reverse(ApiV1DemoUrls.namespace + ApiV1DemoUrls.STACKADEMY_COURSE_CATALOGUE),
        )


class TestVerifyStackademy(TestAccountMixin):
    """Test that verify_stackademy prompts each Stackademy LLMClient, and fails when one doesn't work."""

    def setUp(self):
        super().setUp()
        self.account_number = self.account.account_number
        self.username = self.admin_user.username

    def call(self, *args, **kwargs) -> str:
        """
        Call a manage.py command, and return what it printed.

        :returns: The command's stdout, and anything it printed.
        :rtype: str
        """
        output = io.StringIO()
        with redirect_stdout(output):
            call_command(*args, stdout=output, **kwargs)
        return output.getvalue()

    def test_verify_stackademy(self):
        """Test that verify_stackademy verifies the LLMClients of the account's admin."""
        with mock.patch(f"{MODULE}.Command.verify_llmclients") as verify_llmclients:
            self.call("verify_stackademy", account_number=self.account_number)
        verify_llmclients.assert_called_once_with(user_profile=self.user_profile)

    def test_verify_stackademy_failure(self):
        """Test that verify_stackademy fails when an LLMClient doesn't work."""
        with mock.patch(f"{MODULE}.Command.verify_llmclients", side_effect=CommandError("broken")):
            with self.assertRaises(SystemExit):
                self.call("verify_stackademy", account_number=self.account_number)

    def test_verify_stackademy_unknown_account(self):
        """Test that verify_stackademy verifies nothing for an account that does not exist."""
        with mock.patch(f"{MODULE}.Command.verify_llmclients") as verify_llmclients:
            self.call("verify_stackademy", account_number=UNKNOWN_ACCOUNT_NUMBER)
        verify_llmclients.assert_not_called()

    def test_verify_llmclients(self):
        """Test that verify_llmclients verifies both LLMClients, and deletes its single-use api key."""
        command = verify_stackademy.Command()
        with mock.patch.object(command, "verify_llmclient", side_effect=[None, CommandError("broken")]) as verify:
            with self.assertRaises(CommandError):
                command.verify_llmclients(user_profile=self.user_profile)
        self.assertEqual(
            [call.kwargs["name"] for call in verify.call_args_list], list(verify_stackademy.STACKADEMY_LLMCLIENTS)
        )
        self.assertFalse(SmarterAuthToken.objects.filter(name="verify_stackademy").exists())

    def verify(self, *messages: SmarterDictType, status: int = HTTPStatus.OK) -> str:
        """
        Verify an LLMClient whose chat api answers the prompt with ``messages``.

        :returns: What the command printed.
        """
        config = mock.Mock(status_code=HTTPStatus.OK)
        config.json.return_value = {"data": {"session_key": "a-session-key"}}
        prompt = mock.Mock(status_code=status, content=b"the response")
        prompt.json.return_value = {"api": "smarter.sh/v1", "data": {"status": status, "messages": list(messages)}}
        command = verify_stackademy.Command(stdout=io.StringIO())
        with (
            mock.patch.object(verify_stackademy.LLMClient.objects, "get", return_value=mock.Mock(id=1)),
            mock.patch(f"{MODULE}.APIClient") as api_client,
        ):
            api_client.return_value.post.side_effect = [config, prompt]
            command.verify_llmclient(name="stackademy_api", user_profile=self.user_profile, token_key="a-key")
        paths = [call.args[0] for call in api_client.return_value.post.call_args_list]
        self.assertEqual(paths, ["/api/v1/llm-clients/1/config/", "/api/v1/llm-clients/1/prompt/"])
        return command.stdout.getvalue()

    def test_verify_llmclient(self):
        """Test that an LLMClient works when its plugin returns data and the LLM answers."""
        tool = {"role": "tool", "name": "a_plugin", "content": '[{"course_code": "CS210"}]'}
        output = self.verify(TOOL_CALL, tool, ANSWER)
        self.assertIn("LLMClient stackademy_api works", output)

    def test_verify_llmclient_failures(self):
        """Test that an LLMClient doesn't work without a tool call, its data, or an answer."""
        cases = [([ANSWER], "did not call its plugin")]
        for content in ("", '""', "[]", " "):
            cases.append(([TOOL_CALL, {"role": "tool", "name": "a_plugin", "content": content}, ANSWER], "no data"))
        cases.append(([TOOL_CALL, {"role": "tool", "name": "a_plugin", "content": "not json"}], "did not answer"))
        for messages, error in cases:
            with self.subTest(messages=messages):
                with self.assertRaisesRegex(CommandError, error):
                    self.verify(*messages)

    def test_verify_llmclient_prompt_failure(self):
        """Test that an LLMClient doesn't work when its prompt fails, or its response is invalid."""
        with self.assertRaisesRegex(CommandError, "failed with status 401"):
            self.verify(status=HTTPStatus.UNAUTHORIZED)
        with self.assertRaisesRegex(CommandError, "invalid prompt response"):
            self.verify({"content": "a message without a role"})

    def test_verify_llmclient_does_not_exist(self):
        """Test that verify_llmclient fails for an LLMClient that does not exist."""
        command = verify_stackademy.Command()
        with self.assertRaisesRegex(CommandError, "does not exist"):
            command.verify_llmclient(name=UNKNOWN_LLMCLIENT_NAME, user_profile=self.user_profile, token_key="a-key")

    def test_is_empty_tool_result(self):
        """Test that a tool message whose content is a list of parts is empty only when it has none."""
        is_empty = verify_stackademy.Command.is_empty_tool_result
        self.assertTrue(is_empty(PromptChatApiMessage(role="tool", content=None)))
        self.assertFalse(is_empty(PromptChatApiMessage(role="tool", content=[{"type": "text", "text": "data"}])))
