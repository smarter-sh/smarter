"""Test file handlers utility functions."""

import os
import tempfile
from datetime import datetime

import yaml
from pydantic import SecretStr

from smarter.common.utils import (
    get_readonly_csv_file,
    get_readonly_yaml_file,
)
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestFileHandlersUtils(SmarterTestBase):
    """Test file handlers utility functions."""

    def test_get_readonly_yaml_file(self):
        data = {"foo": "bar"}
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            f.seek(0)
            path = f.name
        try:
            result = get_readonly_yaml_file(path)
            self.assertEqual(result, data)
        finally:
            os.remove(path)

    def test_get_readonly_csv_file(self):
        csv_content = "a,b\n1,2\n3,4\n"
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write(csv_content)
            f.flush()
            f.seek(0)
            path = f.name
        try:
            result = get_readonly_csv_file(path)
            self.assertEqual(result, [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}])
        finally:
            os.remove(path)

    def test_datetime_encoder(self):
        data = {"date": datetime(2024, 1, 1), "secret": SecretStr("abc")}
        encoded = json.dumps(data, cls=json.SmarterJSONEncoder)
        self.assertIn("2024-01-01", encoded)
        self.assertIn("**********", encoded)
