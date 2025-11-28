ADR-018: Caching
================

Status
------
Accepted

Context
-------
Efficient caching is important for performance and scalability. Smarter currently implements its own function results caching using `from smarter.lib.cache import cache_results`. This approach focuses on caching the results of function calls rather than traditional object or instance caching.

Decision
--------
The preferred methodology for caching in this project is to use `cache_results` for function result caching.
Contributors should always attempt to use this approach for caching function outputs.
Example:

.. code-block:: python

  from smarter.lib.cache import cache_results

  @cache_results(timeout=3600, logging_enabled=True)
  def expensive_function(args):
      # hard-to-do computation
      return result

PENDING:
- `cache_results` should be moved into its own independently managed PyPi package.
- This is not a traditional "object caching" solution; it only covers function results, not class instances. This limitation needs to be addressed.

Alternatives Considered
-----------------------
- Implementing traditional object or instance caching.
- Using third-party caching libraries for broader caching needs.

Consequences
------------
- **Positive:**
  - Provides a simple and consistent approach to function result caching.
  - Improves performance for repeated function calls.
- **Negative:**
  - Does not cover object or class instance caching.
  - Requires future work to address broader caching needs.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
