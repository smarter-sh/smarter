"""Tests of scripts/bootstrap_secrets.py, which writes the platform's bootstrap secrets into files (issue #1099)."""

import base64
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bootstrap_secrets  # noqa: E402  pylint: disable=wrong-import-position

SERVICE_ACCOUNT = '{"type": "service_account", "project_id": "test"}'


class TestBootstrapSecrets(unittest.TestCase):
    """Each variable that is set becomes a file named after its Secret; only names are printed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "bootstrap-secrets"

    def test_variables_become_secrets_by_name(self):
        secrets = bootstrap_secrets.bootstrap_secrets(
            {
                "SMARTER_APP_PROVIDER_OPENAI_API_KEY": "sk-test",
                "SMARTER_APP_LLMTOOL_TAVILY_API_KEY": " tvly-test \n",
                "UNRELATED": "x",
            }
        )
        self.assertEqual(secrets, {"openai_api_key": "sk-test", "tavily_api_key": "tvly-test"})

    def test_empty_values_and_placeholders_are_left_out(self):
        secrets = bootstrap_secrets.bootstrap_secrets(
            {
                "SMARTER_APP_PROVIDER_OPENAI_API_KEY": "",
                "SMARTER_APP_PROVIDER_COHERE_API_KEY": "SET-ME-PLEASE",
                "SMARTER_APP_PROVIDER_MISTRAL_API_KEY": "SET-ME-IN-helm/charts/smarter/values.yaml",
            }
        )
        self.assertEqual(secrets, {})

    def test_the_google_service_account_is_decoded(self):
        encoded = base64.b64encode(SERVICE_ACCOUNT.encode()).decode()
        secrets = bootstrap_secrets.bootstrap_secrets({"SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64": encoded})
        self.assertEqual(secrets, {"google_service_account": SERVICE_ACCOUNT})

    def test_invalid_base64_fails_without_its_value(self):
        variables = {"SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64": "not base64!"}
        with self.assertRaises(ValueError) as raised:
            bootstrap_secrets.bootstrap_secrets(variables)
        self.assertNotIn("not base64", str(raised.exception))

    def test_every_secret_name_is_one_that_the_platform_reads(self):
        """The names are those of the Secrets that the init commands look for: the platform's constants."""
        expected = {
            "anthropic_api_key",
            "brave_search_api_key",
            "cohere_api_key",
            "fireworks_api_key",
            "gemini_api_key",
            "google_maps_api_key",
            "google_service_account",
            "llama_api_key",
            "mistral_api_key",
            "openai_api_key",
            "pinecone_api_key",
            "qdrant_cloud_api_key",
            "tavily_api_key",
            "togetherai_api_key",
        }
        self.assertEqual(set(bootstrap_secrets.VARIABLES.values()), expected)

    def test_read_env_file(self):
        env_file = Path(self.tmp.name) / ".env"
        env_file.write_text(
            "# a comment\n"
            "\n"
            'SMARTER_APP_PROVIDER_OPENAI_API_KEY="sk-quoted"\n'
            "export SMARTER_APP_PROVIDER_COHERE_API_KEY=co-test\n"
            "SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64=YWJj==\n"
            "not a variable\n",
            encoding="utf-8",
        )
        variables = bootstrap_secrets.read_env_file(env_file)
        self.assertEqual(variables["SMARTER_APP_PROVIDER_OPENAI_API_KEY"], "sk-quoted")
        self.assertEqual(variables["SMARTER_APP_PROVIDER_COHERE_API_KEY"], "co-test")
        # a value may hold an equals sign.
        self.assertEqual(variables["SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64"], "YWJj==")
        self.assertEqual(len(variables), 3)

    def test_main_writes_files_and_prints_only_names(self):
        env_file = Path(self.tmp.name) / ".env"
        env_file.write_text("SMARTER_APP_PROVIDER_OPENAI_API_KEY=sk-never-printed\n", encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = bootstrap_secrets.main(["--env-file", str(env_file), "--out", str(self.out)])
        self.assertEqual(code, 0)
        self.assertEqual((self.out / "openai_api_key").read_text(encoding="utf-8"), "sk-never-printed")
        self.assertEqual((self.out / "openai_api_key").stat().st_mode & 0o777, 0o644)
        self.assertIn("openai_api_key", stdout.getvalue())
        self.assertNotIn("sk-never-printed", stdout.getvalue())

    def test_main_exits_with_1_on_invalid_base64(self):
        env_file = Path(self.tmp.name) / ".env"
        env_file.write_text("SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64=not-base64!\n", encoding="utf-8")
        with redirect_stderr(io.StringIO()):
            code = bootstrap_secrets.main(["--env-file", str(env_file), "--out", str(self.out)])
        self.assertEqual(code, 1)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
