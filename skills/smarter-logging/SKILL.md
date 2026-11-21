---
name: smarter-logging
description: Use when writing or changing any logger call in Smarter Python code. Every log message starts with a formatted, dot-notated prefix that traces where it came from, which WaffleSwitchedLoggerWrapper writes from the caller's frame (call sites never write logger_prefix, formatted_class_name or a function name), uses lazy %-style arguments, picks its level deliberately, uses a waffle-switched logger where a switch exists, and never logs secrets, credentials or PII (Smarter's log is shown to users in the web console in DEBUG mode).
---

# Smarter Logging Style

The policy is in the Sphinx docs. Read them once, then follow this skill's idioms:

- `docs/source/smarter-framework/developer-reference/lib/logging/logging-style-guide.rst`
- `docs/source/adr/011-logging.rst`
- `docs/source/smarter-framework/developer-reference/lib/logging/waffle-switched-logging.rst`

## The rule: the logger writes the origin, you don't

Every message starts with a formatted (colored) dot-notated path to the code
that logged it, which reads like a stack trace:
`smarter.apps.llmtool.models.plugin_data_api.PluginDataApi.execute_request() API request failed: ...`.
`WaffleSwitchedLoggerWrapper` writes it: each of its logging methods reads the
caller's frame (`smarter.lib.logging.utils.caller_name()`) and puts the name in
front of the message. So a call site writes only its own text:

```python
from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)


def fetch_index_files(url):
    logger.info("downloading %s", url)
```

Details:

- **Never write an origin yourself.** No `logger_prefix`, `module_prefix`,
  `self.formatted_class_name` or `"%s.my_function()"` at the start of a
  message: the wrapper already wrote it, so it would show twice, and a
  hard-coded name goes stale when the function is renamed.
- **The module's logger must be a wrapper**: `logging.getSmarterLogger(__name__)`
  (with switches or without), or `WaffleSwitchedLoggerWrapper(...)`. A plain
  `logging.getLogger(__name__)` logs without the origin. Modules that
  `smarter.lib.logging` itself imports (e.g. `smarter.lib.django.waffle`) can't
  call `getSmarterLogger()` while that package is still initializing; they
  build `WaffleSwitchedLoggerWrapper(logging.getLogger(__name__))`, importing
  the class from `smarter.lib.logging.waffle_switched_logger`.
- **A method is named after the class that runs it**, when its first parameter
  is `self` or `cls`: a base class's method, run by a subclass, logs the
  subclass's name. A staticmethod is named after the class that defines it, a
  nested function as `outer.<locals>.inner()`, and module-level code by its
  module alone.
- Records keep the caller's `funcName` and `lineno`: the wrapper passes
  `stacklevel` to the logger it wraps. A helper that logs on behalf of its
  caller can pass `stacklevel=2` to be named after the caller instead.
- **To color the prefix differently**, so that a family of lines stands out,
  pass `prefix_format`, an ANSI code from `SmarterFormattedText`, to any
  logging method: `logger.debug("called.", prefix_format=logging.SmarterFormattedText.BOLD_DARK_BLUE)`.
  Every `cache_invalidations()` logs its prefix in bold dark blue this way. Only
  a wrapped logger takes it: a plain `logging.Logger` raises `TypeError`.
- Colors are attributes of `SmarterFormattedText`:
  `SmarterFormattedText.text("NOT_READY", SmarterFormattedText.DARK_RED)`.
  `SmarterFormattedText.json()` colors a JSON dump, and `.banner()` frames a
  multi-line message.

## Arguments, not f-strings

Pass values as %-style arguments, so that a message that isn't emitted is never
formatted, and so that log aggregation can group messages by their template:

```python
logger.info("updated %s %s.", self.kind, self.name)    # yes
logger.info(f"updated {self.kind} {self.name}.")       # no
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
```

`WARNING` and above are always emitted, whether or not the switch is on
(`WaffleSwitchedLoggerWrapper.REQUIRED_LOG_LEVEL`). So never put something that
must be seen in production at debug or info behind a switch, and expect debug
and info lines to be missing when a switch is off: don't write tests that
depend on them without turning the switch on.

A new app that logs a lot gets its own switch in
`smarter/lib/django/waffle/switches.py`. Small library modules that log only
warnings and errors use `logging.getSmarterLogger(__name__)` without switches,
which logs at every level the logger is enabled for, and still writes the origin.

## Never log secrets or PII

In DEBUG mode the web console shows Smarter's log to ordinary users, and logs
are also shipped to aggregators. A secret or a person's data in a log entry is
as bad as the same value pushed to this public repository. The rule covers
every level, `print()` and the JavaScript `console.*` calls too.

Never log:

- **Secrets and credentials**: API keys, tokens (including `SmarterAuthToken`
  keys and session keys), passwords, Fernet keys, a Secret's value, cookies,
  `Authorization` headers, connection strings with passwords, signed urls.
- **PII**: email addresses, names, phone numbers, postal addresses, IP
  addresses, payment details, and free text a person typed (a chat prompt, a
  form body), which can hold any of these.
- **Containers of the above**: a whole request, `request.META`, a headers dict,
  `settings`, a manifest or spec dict, a model's `__dict__` or `repr()`, a
  third-party exception whose message echoes the request. Log the fields you
  need, by name.

Identify things instead by id, name of the resource, count or length, or mask
them:

| Value                       | Helper                                                                      |
| --------------------------- | --------------------------------------------------------------------------- |
| Email address               | `smarter.common.utils.mask_email(email)` → `j****@example.com`              |
| Key, token, session key     | `smarter.common.utils.mask_identifier(value)` → `****325c05`                |
| A Secret's dict, a manifest | `redact_secret()` (account data export), `redacted_manifest()` (Kubernetes) |

`mask_string()` is deprecated; don't use it in new code. When you touch a log
call that already breaks this rule, fix it in the same change.

## Tests

Assert on a log call by patching the module's `logger`, not by capturing output.
A patched logger is a mock, so the origin isn't in the message it receives:

```python
with patch.object(system_role, "logger") as logger:
    warn_if_long_system_role(LONG, "field")
logger.warning.assert_called_once()
```

## Checklist

- No log call writes its own origin (`logger_prefix`, `formatted_class_name`,
  a hard-coded `function_name()`): the module's wrapped logger writes it.
- %-style arguments, no f-strings.
- The level matches the table above.
- The module's logger uses its app's waffle switch, if it has one.
- No secret, credential or PII is in the message, its arguments or the
  exception it logs.
