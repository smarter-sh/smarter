---
name: smarter-docstrings
description: Use when writing or editing Python docstrings in Smarter. Docstrings are rendered by Sphinx autodoc into docs.smarter.sh, so they follow the project's reStructuredText field-list style (:param:, :returns:, :raises:), cross-reference syntax, and the layout that pydocstringformatter enforces.
---

# Smarter Python Docstrings

Docstrings do two jobs: they explain the code to developers, and Sphinx autodoc
renders them as the API reference on docs.smarter.sh. Write for a reader who is
new to Smarter, and possibly to Django.

## Style: reStructuredText field lists

The codebase uses reST fields (about 1,850 `:param:` uses), not Google style
(about 100 `Args:` uses, which are legacy). napoleon is enabled, so Google style
renders, but new code uses reST:

```python
def deploy_custom_api(llmclient_id: int) -> Optional[str]:
    """
    Deploy an llmclient on its custom domain: create its custom host's A record and ingress.

    :param llmclient_id: The id of the llmclient.
    :returns: The custom host, e.g. ``support.llmclients.example.com``, or None if the llmclient
        was not deployed on its custom domain, because it does not exist, is not deployed, or its
        custom domain is missing or not verified.
    """
```

- `:param name:` for each parameter. Types come from the annotations
  (`sphinx_autodoc_typehints`), so don't repeat them in `:type:`.
- `:returns:` says what the value means, including `None` cases. Use `:rtype:`
  only when there is no annotation.
- `:raises SomeError: when ...` for each exception that callers should handle.
- Indent continuation lines by four spaces.

## Layout (pydocstringformatter enforces it)

- Opening `"""` on its own line, then a **one-line summary that ends with a
  period**, then a blank line, then the body.
- **Keep the summary to one line.** pydocstringformatter puts a period at the
  end of the first line and splits the body after it. A two-line summary is
  mangled into "Queue the task, which." followed by "creates its hosted
  zone...". About 280 docstrings were repaired by putting each whole first
  sentence on the summary line, the only form the formatter leaves alone. Keep
  it that way.
- A body paragraph starts with a capital letter. A body that starts lower case
  usually means a summary was split.
- Use one blank line between paragraphs, and between the body and the fields.

## Content

- **Module docstrings** say what the module is for, and how it fits in (see
  `smarter/smarter/apps/llmclient/manifest/brokers/custom_domain.py`).
- **Class docstrings** say what the class represents, and its role. Larger
  classes use bold pseudo-headings such as `**Features:**`, `**Parameters:**`,
  and `**Methods:**` (see `SmarterCommand` in
  `smarter/smarter/lib/django/management/base.py`).
- **Functions and methods** cover purpose, parameters, return value, exceptions,
  and side effects: database writes, Celery tasks queued, signals sent, cache
  invalidated, and AWS or Kubernetes calls.
- **Model fields** can be documented with `#:` comments above the field, which
  autodoc picks up:

  ```python
  #: Where the custom domain is in verification. A domain is Verified when its NS records are
  #: delegated to its Route53 hosted zone, and its TLS certificate is issued.
  verification_status = models.CharField(...)
  ```

- Say why, not only what, when the reason isn't obvious. For example: "update(),
  rather than save(), which sends llmclient signals."
- Be accurate. A docstring that describes old behavior is worse than none. When
  you change behavior, update the docstring in the same edit.

## reST inside docstrings

- `double backticks` for literals: field names, values, commands, and file
  names.
- Cross-references: `:class:`~smarter.apps.llmclient.models.LLMClient``,
`:func:`~smarter.apps.llmclient.tasks.verify_custom_domain``, and `:meth:`,
  `:attr:`, `:mod:`. The `~` shows only the last component.
- Example code: `.. code-block:: python` (or `json`, `yaml`), followed by a
  blank line and indented content, or `::` at the end of a paragraph.
- Lists need a blank line before them.

## Test docstrings

A test module has a one-line docstring naming what it tests
(`"""Test SAMCustomDomainBroker."""`). A test method has a one-line docstring
stating the behavior it proves, when the name alone isn't clear:
`"""Apply() creates the CustomDomain, owned by the user."""`.

## Verify

- Run the pre-commit hooks on the file (`smarter-code-quality`): pydocstringformatter
  rewrites docstrings. Review its diff.
- If the object appears in the docs, run
  `skills/smarter-sphinx-docs/scripts/check-docs.sh` on the page that autodocs it
  (`smarter-sphinx-docs`). Don't build the docs.
