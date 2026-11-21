"""
Logging utilities for the Smarter app.

:class:`~smarter.lib.logging.waffle_switched_logger.WaffleSwitchedLoggerWrapper` uses these to start
every log message with the dotted name of the function or method that logged it, so that call sites
never write their own name into a message.
"""

from types import FrameType
from typing import Optional

from smarter.common.helpers.console_helpers import SmarterFormattedText

SELF_PARAMETER_NAMES = ("self", "cls")
"""The names of a method's first parameter that :func:`runtime_class` trusts to be its instance or class."""


def runtime_class(frame: FrameType) -> Optional[type]:
    """
    Return the class that runs the method of a frame, or None if the frame isn't a method's.

    A method inherited from a base class or a mixin is run by the instance's own class, so a log entry
    can say which subclass ran it. The frame's first parameter must be ``self`` or ``cls``, and the class
    that defines the code must be in its class's MRO, so that a function whose first parameter only
    happens to be called ``self`` (e.g. a bound Celery task) keeps its own name.

    :param frame: A frame of the call stack.
    :returns: The class of ``self``, or ``cls`` itself, or None.
    """
    code = frame.f_code
    if code.co_argcount == 0:
        return None
    first_parameter = code.co_varnames[0]
    if first_parameter not in SELF_PARAMETER_NAMES:
        return None
    defining_class_name = code.co_qualname.rpartition(".")[0]
    if not defining_class_name:
        return None
    instance_or_class = frame.f_locals.get(first_parameter)
    if instance_or_class is None:
        return None
    owner = instance_or_class
    if not isinstance(owner, type):
        owner = type(owner)
    for cls in owner.__mro__:
        if cls.__qualname__ == defining_class_name:
            return owner
    return None


def caller_name(frame: FrameType) -> str:
    """
    Return the dotted name of the function or method that a frame is running, for logging.

    :param frame: A frame of the call stack, e.g. the caller of a logging method.
    :returns: The module and qualified name followed by parentheses, e.g.
        ``smarter.apps.llmtool.models.plugin_data_api.PluginDataApi.execute_request()``. A method is
        named after the class that runs it (see :func:`runtime_class`); code at module level is
        named by its module alone.
    """
    module = frame.f_globals.get("__name__", "")
    code = frame.f_code
    if code.co_name == "<module>":
        return module
    qualified_name = code.co_qualname
    owner = runtime_class(frame)
    if owner is not None:
        module = owner.__module__
        qualified_name = f"{owner.__qualname__}.{code.co_name}"
    return f"{module}.{qualified_name}()"


def prefixed_message(prefix: str, msg: object, has_args: bool) -> str:
    """
    Return a log message that starts with a prefix.

    The prefix is written into the message, rather than passed as an argument, so that the message's
    own arguments, including a single mapping for ``%(name)s`` placeholders, are left as they are.

    :param prefix: The formatted prefix, e.g. from :func:`caller_name`.
    :param msg: The message, usually a string with %-style placeholders.
    :param has_args: Whether the message has arguments. If so, a ``%`` in the prefix is escaped,
        because the logging module will %-format the message.
    :returns: The prefix, a space, then the message.
    """
    text = str(msg)
    if has_args:
        prefix = prefix.replace("%", "%%")
    return f"{prefix} {text}"


def formatted_caller_name(frame: FrameType, prefix_format: Optional[str] = None) -> str:
    """
    Return the name of a frame's function or method in the log prefix's color.

    :param frame: A frame of the call stack.
    :param prefix_format: An ANSI format code from :class:`SmarterFormattedText`, e.g.
        ``SmarterFormattedText.BOLD_DARK_BLUE``. None means the usual prefix color,
        :attr:`SmarterFormattedText.DEFAULT`.
    :returns: :func:`caller_name`, formatted with :meth:`SmarterFormattedText.text`.
    """
    name = caller_name(frame)
    if prefix_format is None:
        return SmarterFormattedText.text(name)
    return SmarterFormattedText.text(name, prefix_format)
