"""Test :func:`smarter.lib.manifest.keys.unknown_keys`."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from smarter.lib.manifest.keys import unknown_keys
from smarter.lib.unittest.base_classes import SmarterTestBase


class Header(BaseModel):
    """A model in a list."""

    name: str
    value: str


class Config(BaseModel):
    """A nested model, with an alias, a list of models, and a free-form dict."""

    temperature: Optional[float] = None
    max_tokens: Optional[int] = Field(None, alias="maxTokens")
    headers: Optional[List[Header]] = None
    parameters: Optional[dict[str, Any]] = None


class Spec(BaseModel):
    config: Config
    plugins: Optional[List[str]] = None


class Other(BaseModel):
    other: str


class Manifest(BaseModel):
    kind: str
    spec: Spec


class TestUnknownKeys(SmarterTestBase):
    """Test that the keys that a manifest's model does not define are found, wherever they are."""

    def test_no_unknown_keys(self):
        manifest = {
            "kind": "Test",
            "spec": {
                "config": {
                    "temperature": 0.5,
                    "maxTokens": 10,
                    "headers": [{"name": "a", "value": "b"}],
                    # a dict may have any keys
                    "parameters": {"anything": {"at": "all"}},
                },
                "plugins": ["a", "b"],
            },
        }
        self.assertEqual(unknown_keys(Manifest, manifest), [])

    def test_field_name_and_alias(self):
        self.assertEqual(unknown_keys(Config, {"max_tokens": 1}), [])
        self.assertEqual(unknown_keys(Config, {"maxTokens": 1}), [])

    def test_unknown_keys(self):
        manifest = {
            "kind": "Test",
            "bogus": 1,
            "spec": {
                "config": {
                    "temperatura": 0.5,
                    "headers": [{"name": "a", "value": "b"}, {"name": "c", "val": "d"}],
                },
            },
        }
        self.assertEqual(
            unknown_keys(Manifest, manifest),
            ["bogus", "spec.config.temperatura", "spec.config.headers[1].val"],
        )

    def test_union_of_models(self):
        """Test that a key is known if any of the models that the data may be defines it."""
        self.assertEqual(unknown_keys([Header, Other], {"name": "a", "other": "b"}), [])
        self.assertEqual(unknown_keys([Header, Other], {"nope": 1}), ["nope"])

    def test_values_that_are_not_dicts(self):
        self.assertEqual(unknown_keys(Manifest, None), [])
        self.assertEqual(unknown_keys(Manifest, "text"), [])
        self.assertEqual(unknown_keys(Manifest, {"spec": "not a dict"}), [])
