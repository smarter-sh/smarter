"""Test the base Pydantic models and field validators of :mod:`smarter.lib.manifest.models`."""

from typing import Optional

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.api import SmarterApiVersions
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import (
    AbstractSAMBase,
    AbstractSAMMetadataBase,
    SAMDependency,
    SmarterBasePydanticModel,
)


class Thing(SmarterBasePydanticModel):
    """A concrete model, to test the base model's constructor and validators."""

    label: Optional[str] = None


class TestSmarterBasePydanticModel(TestAccountMixin):
    """Test that a model can be built with a user or a user profile, and that 'None' strings are None."""

    def test_user_profile(self):
        thing = Thing(label="a", user_profile=self.user_profile)
        self.assertEqual(thing.user_profile, self.user_profile)
        self.assertEqual(thing.user, self.admin_user)

    def test_user(self):
        thing = Thing(label="a", user=self.admin_user)
        self.assertEqual(thing.user_profile, self.user_profile)
        self.assertEqual(thing.user, self.admin_user)

    def test_no_user(self):
        thing = Thing(label="a")
        self.assertIsNone(thing.user)
        self.assertIsNone(thing.user_profile)

    def test_none_strings(self):
        self.assertIsNone(Thing(label="None").label)
        self.assertIsNone(Thing(label="").label)
        self.assertEqual(Thing(label="x").label, "x")

    def test_dependency(self):
        self.assertEqual(SAMDependency(kind="LLMClient", name="a").name, "a")


class TestMetadataValidators(TestAccountMixin):
    """Test the metadata's name, version, tags and annotations validators."""

    def test_name(self):
        validate = AbstractSAMMetadataBase.validate_name
        self.assertEqual(validate(" a_name "), "a_name")
        self.assertEqual(validate("a-name"), "a_name")
        self.assertEqual(validate("aName"), "aname")
        for value in (1, "", "a" * 51, "<bad name>"):
            with self.subTest(value=value):
                with self.assertRaises(SAMValidationError):
                    validate(value)

    def test_version(self):
        validate = AbstractSAMMetadataBase.validate_version
        self.assertEqual(validate("1.0.0"), "1.0.0")
        self.assertIsNone(validate(""))
        self.assertIsNone(validate(None))
        with self.assertRaises(SAMValidationError):
            validate("not a version")

    def test_tags(self):
        validate = AbstractSAMMetadataBase.validate_tags
        self.assertIsNone(validate(None))
        self.assertEqual(validate([" a ", 1]), ["a", "1"])
        with self.assertRaises(SAMValidationError):
            validate(["<bad tag>"])

    def test_annotations(self):
        coerce = AbstractSAMMetadataBase.coerce_annotations_to_list
        validate = AbstractSAMMetadataBase.validate_annotations
        self.assertIsNone(coerce(None))
        self.assertEqual(coerce('[{"a": "b"}]'), [{"a": "b"}])
        with self.assertRaises(SAMValidationError):
            coerce("not json")
        self.assertIsNone(validate(None))
        self.assertEqual(validate('[{"a": 1}]'), [{"a": 1}])
        self.assertEqual(validate([{"smarter.sh/a": "b", "c": None}]), [{"smarter.sh/a": "b", "c": None}])
        for value in (
            "not json",
            {"a": "b"},
            ["not a dict"],
            [{"bad key!": "b"}],
            [{"a": object()}],
            [{"a": "x" * 3000}],
        ):
            with self.subTest(value=value):
                with self.assertRaises(SAMValidationError):
                    validate(value)


class TestAbstractSAMBaseValidators(TestAccountMixin):
    """Test the manifest's apiVersion and metadata validators."""

    def test_api_version(self):
        validate = AbstractSAMBase.validate_apiVersion
        self.assertEqual(validate("smarter.sh/v1"), "smarter.sh/v1")
        for value in (None, "", "smarter.sh/v9"):
            with self.subTest(value=value):
                with self.assertRaises(SAMValidationError):
                    validate(value)

    def test_api_versions(self):
        self.assertEqual(SmarterApiVersions.all(), ["smarter.sh/v0", "smarter.sh/v1"])

    def test_metadata(self):
        metadata = AbstractSAMBase.validate_metadata({"name": "a_name", "description": "d", "version": "1.0.0"})
        self.assertIsInstance(metadata, AbstractSAMMetadataBase)
        self.assertIs(AbstractSAMBase.validate_metadata(metadata), metadata)
