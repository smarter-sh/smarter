"""Test :mod:`smarter.apps.api.v1.contract.sam`, the SAM JSON Schemas."""

import glob
import json
import os
import tempfile
from http import HTTPStatus

from jsonschema import Draft202012Validator

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.contract.const import SAM_SCHEMA_DIR, SAM_SCHEMA_SUFFIX
from smarter.apps.api.v1.contract.sam import (
    sam_models,
    sam_schema,
    sam_schema_json,
    sam_schema_path,
    write_sam_schemas,
)
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys


class TestSamSchemas(ApiV1CliTestBase):
    """Test the committed SAM JSON Schemas against the models, and against the cli's responses."""

    def test_every_kind_has_a_model(self):
        self.assertEqual(sorted(sam_models()), sorted(SAMKinds.all()))

    def test_committed_schemas_are_up_to_date(self):
        """The committed sam/<Kind>.schema.json files must be regenerated when a SAM model changes."""
        committed = sorted(path[: -len(SAM_SCHEMA_SUFFIX)] for path in os.listdir(SAM_SCHEMA_DIR))
        self.assertEqual(committed, sorted(sam_models()), "Run `manage.py export_api_contract`.")
        for kind in sam_models():
            with self.subTest(kind=kind):
                with open(sam_schema_path(kind), encoding="utf-8") as file:
                    self.assertEqual(
                        file.read(),
                        sam_schema_json(kind),
                        f"sam/{kind}.schema.json is out of date. Run `manage.py export_api_contract`.",
                    )

    def test_schemas_are_valid_json_schemas(self):
        for kind in sam_models():
            with self.subTest(kind=kind):
                Draft202012Validator.check_schema(sam_schema(kind))

    def test_schemas_are_the_cli_json_schemas(self):
        """A committed schema is exactly the data of the cli's json-schema response."""
        for kind in sam_models():
            with self.subTest(kind=kind):
                response, status = self.get_response(path=f"/api/v1/cli/json-schema/{kind}/")
                self.assertEqual(status, HTTPStatus.OK, response)
                self.assertEqual(response[SmarterJournalApiResponseKeys.DATA], sam_schema(kind))

    def test_example_manifests_are_valid(self):
        """Each kind's example manifest, from the cli, is valid under the kind's schema."""
        for kind in sam_models():
            with self.subTest(kind=kind):
                response, status = self.get_response(path=f"/api/v1/cli/example-manifest/{kind}/")
                self.assertEqual(status, HTTPStatus.OK, response)
                errors = [
                    error.message
                    for error in Draft202012Validator(sam_schema(kind)).iter_errors(
                        response[SmarterJournalApiResponseKeys.DATA]
                    )
                ]
                self.assertEqual(errors, [])

    def test_write_sam_schemas_removes_stale_schemas(self):
        with tempfile.TemporaryDirectory() as directory:
            stale = os.path.join(directory, f"Removed{SAM_SCHEMA_SUFFIX}")
            with open(stale, "w", encoding="utf-8") as file:
                file.write("{}")
            paths = write_sam_schemas(directory)
            self.assertFalse(os.path.exists(stale))
            self.assertEqual(sorted(paths), sorted(glob.glob(os.path.join(directory, f"*{SAM_SCHEMA_SUFFIX}"))))
            with open(sam_schema_path("Guardrail", directory), encoding="utf-8") as file:
                self.assertEqual(json.load(file), sam_schema("Guardrail"))

    def test_unknown_kind(self):
        with self.assertRaises(KeyError):
            sam_schema("NotAKind")
