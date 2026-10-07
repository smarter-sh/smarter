ADR-027: Python Annotations
===========================

Status
------
Accepted

Context
-------
Strong typing improves code quality, maintainability, and tooling support. Type annotations help catch errors early and provide better documentation for contributors.

Decision
--------
Python code in this project is strongly typed. Contributors should use type annotations throughout the codebase. For example:

.. code-block:: python

    def __init__(
        self,
        *args,
        user_profile: Optional[UserProfile] = None,
        selected: bool = False,
        api_version: Optional[str] = None,
        manifest: Optional[SAMPluginCommon] = None,
        plugin_id: Optional[int] = None,
        plugin_meta: Optional[PluginMeta] = None,
        data: Union[dict[str, Any], str, None] = None,
        name: Union[str, None] = None,
        **kwargs,
    ):

To the extent that Python requirements are added to this project, any available corresponding stubs/annotation packages should be added in kind to `smarter/requirements/in/local.in`. Example:

.. code-block:: console

    django-stubs==5.2.2                 # Type annotations for Django
    djangorestframework-stubs==3.16.0   # type annotations for djangorestframework
    mypy_extensions==1.1.0              # Type annotations for Python

Alternatives Considered
-----------------------
- Not using type annotations.
- Relying solely on dynamic typing.

Consequences
------------
- **Positive:**
  - Improves code reliability and maintainability.
  - Enables better static analysis and tooling.
  - Reduces runtime errors due to type mismatches.
- **Negative:**
  - Requires contributors to be familiar with Python type hints.
  - May require additional effort to maintain type stubs and annotations.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
