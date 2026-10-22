---
name: smarter-logging
description: Use when writing or changing any logger call in Smarter Python code. Every log message starts with a formatted, dot-notated prefix that traces where it came from (logger_prefix or formatted_class_name), uses lazy %-style arguments, picks its level deliberately, uses a waffle-switched logger where a switch exists, and never logs secrets.
---

# Smarter Logging Style

The policy is in the Sphinx docs. Read them once, then follow this skill's idioms:

- `docs/source/smarter-framework/developer-reference/lib/logging/logging-style-guide.rst`
- `docs/source/adr/011-logging.rst`
- `docs/source/smarter-framework/developer-reference/lib/logging/waffle-switched-logging.rst`

## The rule: every message starts with its origin

Each message's first argument is a formatted (colored) dot-notated path to the
code that logged it, followed by the **unformatted** function or method name.
Together they read like a stack trace: `smarter.apps.llmtool.extension.registry.fetch_index_files() ...`.
A message without the prefix can't be traced, and is a defect in review.

**Module-level code** (functions, receivers, tasks, management command helpers):

```python
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


def fetch_index_files(url):
    logger.info("%s.fetch_index_files() downloading %s", logger_prefix, url)
```

**Methods of a class** that has `formatted_class_name` (anything built on
`SmarterHelperMixin`, e.g. brokers, models, plugins, views):

```python
logger.warning(
    "%s.authenticate(): invalid api_token type: %s. Expected bytes.",
    self.formatted_class_name,  # cls.formatted_class_name in a classmethod
    type(api_token),
)
```

A class without `formatted_class_name` uses the module's `logger_prefix` plus
`ClassName.method()`: `"%s.CharacterForeignKey.add_sql() ..."`.

Details:

- Format only the prefix (`formatted_text()`), never the function name. Write
  the name with `()`, and keep it right when you rename the function.
- Prefer `logging.formatted_text(__name__)`, the most common form, over
  `formatted_text(f"{__name__}")` or a hard-coded module path, which goes stale
  when the module moves.
- `formatted_class_name` is the **runtime** class. In a base class's method, a
  subclass's name is logged, which is usually what you want; say so if not.

## Arguments, not f-strings

Pass values as %-style arguments, so that a message that isn't emitted is never
formatted, and so that log aggregation can group messages by their template:

```python
logger.info("%s.apply() updated %s %s.", self.formatted_class_name, self.kind, self.name)  # yes
logger.info(f"{self.formatted_class_name}.apply() updated {self.kind} {self.name}.")       # no
```

## Levels

| Level     | Use it for                                                                                         |
| --------- | -------------------------------------------------------------------------------------------------- |
| `debug`   | Detail for a developer tracing a flow: arguments, intermediate values, cache hits.                 |
| `info`    | A normal event worth a line in production: a resource created, a task finished, a table converted. |
| `warning` | Something unusual that was handled: a fallback, a retry, a value that is allowed but suspicious.   |
| `error`   | Something failed and needs attention: a request, task or apply that did not do its job.            |

- An expected answer is not an error. A validator asked "is this valid?" that
  answers no must not log at ERROR.
- Log an exception once, where it is handled, not at every level it passes
  through. Constructing a `SmarterException` logs it at DEBUG only, so the
  handler is responsible for logging it at the level the outcome deserves. Include the exception in the message (`"...: %s", e`), or use
  `logger.exception()` inside an `except` when the traceback matters.

## Waffle-switched loggers

Apps with a `SmarterWaffleSwitches.*_LOGGING` switch log through it, so that
their debug and info output can be turned on at runtime without a redeploy.
The newest form (prefer it to the hand-written `should_log` +
`WaffleSwitchedLoggerWrapper` that ADR-011 shows; they are equivalent):

```python
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING])
logger_prefix = logging.formatted_text(__name__)
```

`WARNING` and above are always emitted, whether or not the switch is on
(`WaffleSwitchedLoggerWrapper.REQUIRED_LOG_LEVEL`). So never put something that
must be seen in production at debug or info behind a switch, and expect debug
and info lines to be missing when a switch is off: don't write tests that
depend on them without turning the switch on.

A new app that logs a lot gets its own switch in
`smarter/lib/django/waffle/switches.py`. Small library modules that log only
warnings and errors may use plain `logging.getLogger(__name__)`.

## Never log secrets

The repository is public and logs are shipped to aggregators. Never log an API
key, token, password, Fernet key, `Authorization` header, or a whole headers
dict or settings object. When a credential must be identified, mask it:
`smarter.common.utils.mask_string(key)` or `self.mask_string(key)`.

## Tests

Assert on a log call by patching the module's `logger`, not by capturing output:

```python
with patch.object(system_role, "logger") as logger:
    warn_if_long_system_role(LONG, "field")
logger.warning.assert_called_once()
```

## Checklist

- Every new or changed log call starts with `logger_prefix` or
  `formatted_class_name`, then `.function_name()`.
- %-style arguments, no f-strings.
- The level matches the table above.
- The module's logger uses its app's waffle switch, if it has one.
- Nothing secret is in the message or its arguments.
