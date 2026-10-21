"""Test the export_llmclient_architecture management command."""

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.lib.manifest.models import SAMDependencyTreeNode


class TestExportLLMClientArchitecture(TestAccountMixin):
    """Test that an LLMClient's architecture is written as JSON, and without owners or urls with --public."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name="test_export_llmclient_architecture", user_profile=cls.user_profile
        )
        cls.guardrail = Guardrail.objects.create(
            user_profile=cls.user_profile,
            name="test_export_llmclient_architecture_guardrail",
            description="test",
            version="1.0.0",
            stage="both",
            category="pii",
        )
        LLMClientGuardrails.objects.create(llmclient=cls.llmclient, guardrail=cls.guardrail)

    @classmethod
    def tearDownClass(cls):
        LLMClientGuardrails.objects.filter(llmclient=cls.llmclient).delete()
        Guardrail.objects.filter(pk=cls.guardrail.pk).delete()
        LLMClient.objects.filter(pk=cls.llmclient.pk).delete()
        super().tearDownClass()

    def export(self, *args: str) -> SAMDependencyTreeNode:
        """Run the command into a file, and read the tree that it wrote."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "architecture.json"
            call_command(
                "export_llmclient_architecture",
                "--name",
                self.llmclient.name,
                "--account_number",
                self.account.account_number,
                "--output",
                str(output),
                *args,
                stdout=StringIO(),
            )
            return SAMDependencyTreeNode.model_validate(json.loads(output.read_text(encoding="utf-8")))

    def test_tree(self):
        """The tree is the LLMClient's, as its owner sees it, with owners and web console urls."""
        tree = self.export()
        self.assertEqual((tree.kind, tree.name), ("LLMClient", self.llmclient.name))
        self.assertEqual(tree.recordLocator, self.llmclient.record_locator)
        self.assertTrue(tree.readable)
        self.assertIn(self.admin_user.username, tree.owner)
        self.assertTrue(tree.url)
        guardrails = [child for child in tree.children if child.kind == "Guardrail"]
        self.assertEqual([child.name for child in guardrails], [self.guardrail.name])
        self.assertTrue(guardrails[0].owner)

    def test_public(self):
        """--public leaves out every node's owner and url, and keeps the rest."""
        tree = self.export("--public")
        self.assertEqual((tree.kind, tree.name), ("LLMClient", self.llmclient.name))
        self.assertEqual(tree.recordLocator, self.llmclient.record_locator)
        nodes = [tree, *tree.children]
        self.assertGreater(len(nodes), 1)
        for node in nodes:
            self.assertIsNone(node.owner, node.kind)
            self.assertIsNone(node.url, node.kind)
        self.assertIn(self.guardrail.name, [child.name for child in tree.children])

    def test_stdout(self):
        """Without --output, the tree is written to standard output."""
        out = StringIO()
        call_command(
            "export_llmclient_architecture",
            "--name",
            self.llmclient.name,
            "--account_number",
            self.account.account_number,
            stdout=out,
        )
        tree = json.loads(out.getvalue())
        self.assertEqual(tree["name"], self.llmclient.name)

    def test_no_llmclient(self):
        """An LLMClient that the account doesn't have is an error."""
        with self.assertRaises(CommandError):
            call_command(
                "export_llmclient_architecture",
                "--name",
                "no_such_llmclient",
                "--account_number",
                self.account.account_number,
                stdout=StringIO(),
            )
