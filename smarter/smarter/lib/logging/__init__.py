"""
A logger that can be controlled with a condition function.
This allows for more flexible logging behavior based on runtime conditions.
"""

from logging import (
    BASIC_FORMAT,
    CRITICAL,
    DEBUG,
    ERROR,
    FATAL,
    INFO,
    NOTSET,
    WARN,
    WARNING,
    BufferingFormatter,
    FileHandler,
    Filter,
    Formatter,
    Handler,
    Logger,
    LoggerAdapter,
    LogRecord,
    NullHandler,
    StreamHandler,
    addLevelName,
    basicConfig,
    captureWarnings,
    critical,
    debug,
    disable,
    error,
    exception,
    fatal,
    getHandlerByName,
    getHandlerNames,
    getLevelName,
    getLevelNamesMapping,
    getLogger,
    getLoggerClass,
    getLogRecordFactory,
    info,
    lastResort,
    log,
    makeLogRecord,
    raiseExceptions,
    setLoggerClass,
    setLogRecordFactory,
    shutdown,
    warn,
    warning,
)
from typing import Callable, Optional, Union

from smarter.lib.django.waffle import switch_is_active

from .redis_log_handler import (
    GLOBAL_LOG_CHANNEL,
    RedisLogHandler,
    current_job_id,
    job_id_factory,
)
from .streaming_file_handler import StreamingFileHandler
from .waffle_switched_logger import WaffleSwitchedLoggerWrapper


def getSmarterLogger(
    name=None,
    any_switches: Optional[list[str]] = None,
    all_switches: Optional[list[str]] = None,
    condition_func: Optional[Callable[[], bool]] = None,
) -> Union[Logger, WaffleSwitchedLoggerWrapper]:
    """
    Python's logging module enhanced with optional Waffle switch control. If
    any of `any_switches`, `all_switches` or `condition_func` is provided, the
    logger will only emit logs if at least one of the specified conditions is met.

    :param name: The name of the logger to retrieve. If None, the root logger is returned.
    :param any_switches: An optional list of Waffle switch names to control logging output.
       Any switch in this list being active will enable logging output.
    :param all_switches: An optional list of Waffle switch names to control logging output.
       All switches in this list must be active to enable logging output.
    :param condition_func: An optional callable that returns a boolean to control logging output.
       If provided, logging will only occur if this function returns True.
    :return: A logger instance that may be wrapped with Waffle switch control.
    :rtype: Logger or WaffleSwitchedLoggerWrapper
    """

    def eval_any_switches() -> bool:
        return (
            isinstance(any_switches, list)
            and len(any_switches) > 0
            and any(switch_is_active(switch) for switch in any_switches)
        )

    def eval_all_switches() -> bool:
        return (
            isinstance(all_switches, list)
            and len(all_switches) > 0
            and all(switch_is_active(switch) for switch in all_switches)
        )

    def eval_switches() -> bool:
        return eval_any_switches() or eval_all_switches() or (condition_func() if condition_func is not None else False)

    def switches_are_provided() -> bool:
        return (isinstance(any_switches, list) and len(any_switches) > 0) or (
            isinstance(all_switches, list) and len(all_switches) > 0 or condition_func is not None
        )

    logger = getLogger(name)

    if switches_are_provided():
        logger = WaffleSwitchedLoggerWrapper(logger, eval_switches)
    return logger


__all__ = [
    "WaffleSwitchedLoggerWrapper",
    "current_job_id",
    "job_id_factory",
    "StreamingFileHandler",
    "RedisLogHandler",
    "GLOBAL_LOG_CHANNEL",
    "BASIC_FORMAT",
    "BufferingFormatter",
    "CRITICAL",
    "DEBUG",
    "ERROR",
    "FATAL",
    "FileHandler",
    "Filter",
    "Formatter",
    "Handler",
    "INFO",
    "LogRecord",
    "Logger",
    "LoggerAdapter",
    "NOTSET",
    "NullHandler",
    "StreamHandler",
    "WARN",
    "WARNING",
    "addLevelName",
    "basicConfig",
    "captureWarnings",
    "critical",
    "debug",
    "disable",
    "error",
    "exception",
    "fatal",
    "getLevelName",
    "getLogger",
    "getLoggerClass",
    "info",
    "log",
    "makeLogRecord",
    "setLoggerClass",
    "shutdown",
    "warn",
    "warning",
    "getLogRecordFactory",
    "setLogRecordFactory",
    "lastResort",
    "raiseExceptions",
    "getLevelNamesMapping",
    "getHandlerByName",
    "getHandlerNames",
]
