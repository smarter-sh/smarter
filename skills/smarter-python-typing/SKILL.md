---
name: smarter-python-typing
description: Use when writing or reviewing Python type annotations in Smarter, especially any use of typing.Any, Optional[Any], list[Any], or dict[str, Any], or a type construction that is repeated across the codebase. Explains when Any is honest and when it hides a finite set of types, the Smarter-prefixed aliases in smarter.lib.typing (e.g. SmarterDictType), and when to add a new alias.
---

# Smarter Python Type Annotations

An annotation is a claim about what a value can be. Readers, type checkers and
Sphinx autodoc (which publishes the signatures on docs.smarter.sh) all take it
at its word. `Any` makes the weakest possible claim and also turns the type
checker off for that value, so it's only correct when the claim is literally
true.

## When `Any` is acceptable

Use `Any` only where the value really can be of any type, and no narrower type
would be true.

```python
def status(self, now: Optional[datetime] = None) -> dict[str, Any]:
```

This is fine. The values of a status report are strings, numbers, booleans,
lists and nested dicts, and any of them may be added later. (Spell it
`SmarterDictType`; see [Aliases](#aliases-in-smarterlibtyping).)

Other honest uses:

- `*args: Any, **kwargs: Any` that are passed through to someone else's API.
- Comparison dunders: `def __eq__(self, other: Any) -> bool`.
- Values stored in a generic container: cache values (`lazy_cache.set(key, value: Any)`),
  a log message (`msg: Any`).
- Validators and normalizers whose job is to accept untrusted input of any type
  and reject or coerce it: `positive_int(value: Any, ...)`,
  `normalize_country(value: Any)`, arguments that an LLM supplies to a tool.
- A value that is only stored, compared or passed on can also be `object`,
  which accepts anything but keeps the type checker on: a function that
  calls a method on an `object` fails type checking, one on `Any` doesn't.
- Defensive pass-throughs that accept anything, transform the values they
  recognize, and return everything else unchanged, e.g.
  `without_diagnostics(response: Any) -> Any` in `apps/prompt/contract/builders.py`.

## When `Any` is wrong

If you can list the types a value can take, list them. `Any` there hides
information that the reader and the type checker need.

```python
# wrong: yaml.safe_load() returns what the file holds
def load_yaml(path: str) -> Any:

# right, for a function whose callers read a mapping, or iterate a list
def load_yaml(path: str) -> Union[SmarterDictType, list[SmarterDictType], None]:
```

The typical mistakes:

- **A return type with a finite set of possibilities.** Write the `Union`, or
  `Optional[...]` when the alternative is `None`. If callers must then narrow
  it, that's the truth about the function. Consider splitting it into two
  functions, each with one return type.
- **`Optional[Any]`**. `Any` already includes `None`, so it says nothing more
  than `Any`. Either the value has a real type (`Optional[LLMClient]`), or it's `Any`.
- **`Any` to dodge a circular import.** Import the class under
  `if TYPE_CHECKING:` and annotate with it (as a string where needed):

  ```python
  from typing import TYPE_CHECKING, Optional

  if TYPE_CHECKING:
      from smarter.apps.llmclient.models import LLMClient

  def for_llmclient(cls, llmclient: Optional["LLMClient"]) -> "GuardrailPipeline":
  ```

- **A third-party object whose type you didn't look up**, e.g. a Redis client,
  a boto3 response, an NLTK corpus reader, a DRF `Request`. Look it up, and
  import it under `TYPE_CHECKING` if importing it at runtime is expensive.
- **Parsed JSON.** A value that is any JSON is `pydantic.JsonValue`, not `Any`.
  `JsonValue` is exactly JSON (`None`, `bool`, `int`, `float`, `str`, and
  lists and dicts of those). A JSON object or list whose shape you know gets a
  Pydantic model (see "Pydantic over JSON" in `smarter-development` and ADR-031).
- **A return type that depends on an argument's type.** Use `@overload`, e.g.
  `to_snake_case()` (str to str, dict to dict, list to list) in
  `common/utils/conversion.py`, and `get_env()` (whose return type follows its
  `default`) in `common/conf/env.py`. A `TypeVar` does the same for a function
  that returns the very object it was given.
- **`:type ...: Any` or `:rtype: Any` in a docstring.** Keep the docstring in
  step with the annotation.

## Aliases in `smarter.lib.typing`

A type construction that appears more than about ten times in the codebase is
declared once in `smarter/smarter/lib/typing.py`, named `Smarter<Name>Type`:

| Alias             | Means            | Use for                                          |
| ----------------- | ---------------- | ------------------------------------------------ |
| `SmarterDictType` | `dict[str, Any]` | a mapping whose values really can be of any type |

```python
from smarter.lib.typing import SmarterDictType

def to_json(self) -> SmarterDictType:
def rows(self) -> list[SmarterDictType]:
def config(self) -> Optional[SmarterDictType]:
```

- **Use the alias**, not the construction it stands for. Don't write
  `dict[str, Any]` in new code.
- **A bare `dict` annotation is a `SmarterDictType`.** Our dicts have string
  keys, so `Optional[dict]`, `list[dict]` and `-> dict` are spelled
  `Optional[SmarterDictType]` and so on. Two exceptions: a dict whose keys
  aren't strings says so (`dict[SAMKeys, Any]` in `lib/manifest/loader.py`),
  and a Pydantic model field that holds user-supplied YAML stays a bare
  `dict`, because `dict[str, Any]` makes Pydantic reject a mapping with
  non-string keys, e.g. `200:`.
- **Compose it** with `Optional[...]`, `list[...]` and `Union[...]` at the point
  of use. Don't add aliases such as `SmarterOptionalDictType`. They multiply
  without adding meaning.
- **An alias doesn't make a loose type right.** `SmarterDictType` still claims
  that the values can be anything. A dict whose values are all strings is
  `dict[str, str]`, and a structured JSON document is a Pydantic model.
- **Add an alias** when a construction that carries meaning, such as one with
  `Any`, a nested container, or a long `Union`, recurs about ten times or more
  across modules. Name it `Smarter<Name>Type`, give it a docstring (Sphinx
  publishes it), add it to `__all__` and to the table above, and replace the
  existing uses in the same change.
- **Don't alias** single-level builtin generics of concrete types
  (`list[str]`, `dict[str, str]`) or `Optional[X]`. They're already as clear
  as a name would be. Don't alias something used only within one module,
  either. A module-level alias there is enough.
- `smarter.lib.typing` imports only from the standard library, so that any
  module, including `smarter.common.conf.settings`, can import it without an
  import cycle. Keep it that way.

## Checking your work

```bash
# Any in annotations (not prose such as "Any exception ..."), in the files you changed
git diff --name-only -- '*.py' | xargs grep -nE '(: *|-> *|\[)Any\b'
```

For each hit, ask: can I list the types this value can have? If so, list them.
