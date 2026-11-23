System Administration
=====================

The day-to-day work of running a Smarter platform once it is installed: keeping it up to date and
its data backed up, its accounts, users and API keys, its LLM providers and extensions, its costs,
its audit trail and its security. Most of it is
done in the :doc:`web console <system-administration/tools/smarter-web-console>`, the :doc:`Django admin <system-administration/tools/django-admin>`, or with
the platform's ``manage.py`` commands. For the cluster itself, its sizing, monitoring, pod logs and
housekeeping, see :doc:`../smarter-framework/smarter-on-kubernetes/operations`.

.. toctree::
   :maxdepth: 2

   system-administration/operations
   system-administration/tools
   system-administration/accounts-and-access
   system-administration/llm-providers-and-extensions
   system-administration/costs-and-auditing
   system-administration/security
