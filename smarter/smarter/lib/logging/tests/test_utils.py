"""Test :mod:`smarter.lib.logging.utils`."""

import sys
from types import FrameType

from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib.logging.utils import (
    caller_name,
    formatted_caller_name,
    prefixed_message,
    runtime_class,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


def current_frame() -> FrameType:
    """Return the frame of this function's caller."""
    return sys._getframe(1)  # pylint: disable=protected-access


def plain_function() -> FrameType:
    """Return a module-level function's own frame."""
    return current_frame()


def function_with_a_self_parameter(self) -> FrameType:  # pylint: disable=unused-argument
    """Return the frame of a module-level function whose first parameter is called ``self``, like a bound Celery task."""
    return current_frame()


class Base:
    """A class whose methods a subclass inherits."""

    def instance_method(self) -> FrameType:
        """Return the method's own frame."""
        return current_frame()

    @classmethod
    def class_method(cls) -> FrameType:
        """Return the classmethod's own frame."""
        return current_frame()

    @staticmethod
    def static_method() -> FrameType:
        """Return the staticmethod's own frame."""
        return current_frame()


class Subclass(Base):
    """A subclass that inherits every method of Base."""


class TestRuntimeClass(SmarterTestBase):
    """Test runtime_class()."""

    def test_instance_method(self):
        self.assertIs(runtime_class(Subclass().instance_method()), Subclass)

    def test_classmethod(self):
        self.assertIs(runtime_class(Subclass.class_method()), Subclass)

    def test_staticmethod_has_none(self):
        self.assertIsNone(runtime_class(Subclass.static_method()))

    def test_function_has_none(self):
        self.assertIsNone(runtime_class(plain_function()))

    def test_a_self_parameter_outside_a_class_has_none(self):
        """A function's parameter named self, whose class doesn't define the function, isn't trusted."""
        self.assertIsNone(runtime_class(function_with_a_self_parameter(object())))


class TestCallerName(SmarterTestBase):
    """Test caller_name()."""

    def test_function(self):
        self.assertEqual(caller_name(plain_function()), f"{__name__}.plain_function()")

    def test_method(self):
        self.assertEqual(caller_name(Base().instance_method()), f"{__name__}.Base.instance_method()")

    def test_inherited_method_is_named_after_the_subclass(self):
        self.assertEqual(caller_name(Subclass().instance_method()), f"{__name__}.Subclass.instance_method()")

    def test_inherited_classmethod_is_named_after_the_subclass(self):
        self.assertEqual(caller_name(Subclass.class_method()), f"{__name__}.Subclass.class_method()")

    def test_staticmethod_is_named_after_the_class_that_defines_it(self):
        self.assertEqual(caller_name(Subclass.static_method()), f"{__name__}.Base.static_method()")

    def test_nested_function(self):
        def inner() -> FrameType:
            return current_frame()

        expected = f"{__name__}.TestCallerName.test_nested_function.<locals>.inner()"
        self.assertEqual(caller_name(inner()), expected)

    def test_formatted(self):
        expected = SmarterFormattedText.text(f"{__name__}.plain_function()")
        self.assertEqual(formatted_caller_name(plain_function()), expected)

    def test_formatted_with_a_prefix_format(self):
        blue = SmarterFormattedText.BOLD_DARK_BLUE
        expected = SmarterFormattedText.text(f"{__name__}.plain_function()", blue)
        self.assertEqual(formatted_caller_name(plain_function(), blue), expected)


class TestPrefixedMessage(SmarterTestBase):
    """Test prefixed_message()."""

    def test_with_arguments_escapes_the_prefix(self):
        self.assertEqual(prefixed_message("50%", "%s done", has_args=True), "50%% %s done")

    def test_without_arguments_keeps_the_prefix(self):
        self.assertEqual(prefixed_message("50%", "done", has_args=False), "50% done")

    def test_message_that_is_not_a_string(self):
        self.assertEqual(prefixed_message("prefix", ValueError("bad"), has_args=False), "prefix bad")
