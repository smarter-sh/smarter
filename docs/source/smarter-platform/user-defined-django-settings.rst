User-Defined Django Settings
============================

Smarter is a Django application, and you can set any Django setting yourself, without changing
Smarter's code: a session's lifetime, the administrators' email addresses, a Content Security Policy,
a setting of a Django package that you add. Your settings supersede Smarter's own values, in every
environment.

.. danger::

   **A user-defined setting is a hammer. Use it with care.**

   It replaces Smarter's value of that setting outright, in every environment where it applies, however
   carefully Smarter's value was built. Smarter does nothing to stop you, and doesn't warn you:

   - **Smarter's settings are often computed, not constant.** ``base.py``, ``base_aws.py`` and each
     environment's module build many settings from other settings and from ``smarter_settings``: the
     database, the caches and their separate Redis databases for sessions and Celery, storage on S3 or on
     disk, allowed hosts, CORS and CSRF origins, cookie security, the Content Security Policy's sources. Your
     value replaces the result of all that, and nothing that was derived from the old value is computed
     again.
   - **Lists and dictionaries are replaced whole, not merged.** A ``LOGGING``, ``CACHES``, ``DATABASES`` or
     ``MIDDLEWARE`` that leaves out one of Smarter's entries removes it, with whatever it did.
   - **Only the type is checked, never the meaning.** ``SESSION_COOKIE_SECURE: false`` in prod is a valid
     setting: the session cookie is then sent without HTTPS. A wrong value can stop the platform, or, worse,
     keep it running with weaker security, and nothing tells you so.
   - **It applies to every pod.** In Kubernetes, the api, the workers, beat, and the init and migrate jobs
     all read the same settings.

   So, before you override a setting:

   1. Read how Smarter sets it, in ``smarter/settings/``, and what else is built from it.
   2. Prefer a ``SMARTER_*`` setting where one exists (see :doc:`configuration`): Smarter derives every
      dependent setting from it, correctly.
   3. Change as few settings as you can, and for a list or a dictionary, start from a copy of Smarter's whole
      value.
   4. Try the change locally, and then in alpha, before prod.

   To undo a setting, delete it from your file or your variables: Smarter's own value applies again.

.. important::

   **Where your settings go depends on where Smarter runs.** There are two places, and each one is read
   in one kind of environment only:

   .. list-table::
      :header-rows: 1
      :widths: 30 35 35

      * - Where Smarter runs
        - Put your settings in
        - Never in
      * - **Local development**, on your computer, with Docker Compose (``make run``)
        - ``user-settings/settings.yaml``, in the repository's root
        - The Helm chart: nothing local reads it
      * - **alpha, beta, next, prod**, and every other environment on AWS (Kubernetes)
        - ``DJANGO_<SETTING>`` variables in ``env`` in the Helm chart's values
        - ``user-settings/``: it is **never** built into the Docker image, and no deployed pod reads it

   A setting that you put in ``user-settings/settings.yaml`` changes your own computer only. To change
   alpha or prod, change the Helm values that their deployment uses.

The same code applies both: :mod:`smarter.settings.user`. ``DJANGO_*`` variables work locally too, in
``.env``.

How your settings supersede Smarter's
-------------------------------------

Django reads one settings module, named by ``DJANGO_SETTINGS_MODULE``: ``smarter.settings.local`` on your
computer, ``smarter.settings.prod`` in prod, and so on. Each of those modules builds on the ones before it,
and your settings come last. From lowest to highest priority:

1. ``smarter/settings/base.py``, Smarter's settings for every environment.
2. ``smarter/settings/base_aws.py``, Smarter's settings for the environments on AWS. Local development
   skips it.
3. The environment's own module: ``local.py``, ``alpha.py``, ``beta.py``, ``next.py`` or ``prod.py``.
4. **Your settings file**, ``user-settings/settings.yaml``, locally.
5. **Your** ``DJANGO_*`` **environment variables**, e.g. ``DJANGO_SESSION_COOKIE_AGE=3600``.

A later step wins. So your settings supersede everything that Smarter sets, and a variable supersedes
your file. For example, ``base_aws.py`` sets ``SESSION_COOKIE_SECURE = True`` for alpha and prod. With
this in the Helm values:

.. code-block:: yaml

   env:
     DJANGO_SESSION_COOKIE_SECURE: "false"

prod runs with ``SESSION_COOKIE_SECURE = False``.

Every environment's module ends the same way: it applies your settings, then logs its configuration. So
what the log shows is what Django runs with, your settings included, and no line of Smarter's settings
can undo yours.

Local development
-----------------

This is for your own computer only. See the note at the top of this page.

1. Copy the example to the file that Smarter reads. Git ignores ``settings.yaml``, so your settings stay
   on your computer:

   .. code-block:: console

      cp user-settings/settings.example.yaml user-settings/settings.yaml

2. Uncomment and edit the settings that you want, or write your own, one setting per key:

   .. code-block:: yaml

      SESSION_COOKIE_AGE: 3600
      ADMINS:
        - you@example.com

3. Restart the containers that load Django's settings:

   .. code-block:: console

      docker compose restart smarter-api smarter-worker smarter-worker-infrastructure smarter-beat

Docker Compose mounts ``user-settings/`` read-only at ``/home/smarter_user/user-settings/`` in those four
containers, which is where :mod:`smarter.settings.user` looks for ``settings.yaml``. A missing file is not
an error: there are simply no user settings.

For a ``DJANGO_*`` variable, add it to ``.env``, e.g. ``DJANGO_SESSION_COOKIE_AGE=3600``, and recreate the
containers (``make run``), since Docker Compose reads ``.env`` when it creates them.

The test shards (``make docker-test-sharded``) don't mount ``user-settings/``, so your settings don't change
their results. Tests that you run in the dev containers with ``docker exec`` do read your file.

alpha, prod, and every other environment on AWS
-----------------------------------------------

Here your settings go in the Helm chart's values, never in ``user-settings/``. Add a ``DJANGO_<SETTING>``
variable for each one to ``env``, in the values file that your deployment passes to ``helm upgrade`` (or in
``helm/charts/smarter/values.yaml``). Quote every value: the chart's environment is strings. A list or a
dictionary is JSON:

.. code-block:: yaml

   env:
     DJANGO_SESSION_COOKIE_AGE: "3600"
     DJANGO_ADMINS: '["ops@example.com"]'
     DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE: "10485760"

The chart stores ``env`` in the Kubernetes Secret ``<appName>-env``, which every pod reads as its
environment, so a value may be a password. A change to it changes the pods' ``checksum/env`` annotation,
so ``helm upgrade`` rolls the api, worker and beat pods, which then read the new settings.

``DJANGO_*`` environment variables
----------------------------------

Besides the file, :mod:`smarter.settings.user` reads every environment variable whose name starts with
``DJANGO_``, and sets the Django setting named by the rest of it: ``DJANGO_SESSION_COOKIE_AGE=3600`` sets
``SESSION_COOKIE_AGE``. It does so in every environment, right after it applies the file, so:

- a variable supersedes the same setting in your file, and every value in Smarter's settings;
- it is the quickest way to change one setting, without writing a file.

Where to set one:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Where Smarter runs
     - Where the variable goes
   * - Local development
     - ``.env``, in the repository's root. Recreate the containers (``make run``) afterwards: Docker
       Compose reads ``.env`` when it creates them.
   * - alpha, prod, and every other environment on AWS
     - ``env`` in the Helm chart's values, e.g. ``DJANGO_SESSION_COOKIE_AGE: "3600"``. The chart stores
       ``env`` in the Secret ``<appName>-env``, which every pod reads as its environment.

A variable's value is text, and is converted to the type of the setting's value, as `Writing values`_
explains: ``true`` for a boolean, ``3600`` for an integer, ``a,b`` or a JSON list for a list. A nested
setting, such as ``LOGGING``, is easier to write in the file. ``DJANGO_SETTINGS_MODULE`` is Django's own,
and is not a setting; it is left alone.

Writing values
--------------

A file's value is YAML, and is used as it is. An environment variable's value is text, and is converted to
the type of the setting's value before it: the value from Smarter's settings and your file, or else
Django's own default for that setting.

.. list-table::
   :header-rows: 1
   :widths: 18 40 42

   * - Kind of value
     - In the file (YAML)
     - As an environment variable
   * - Integer
     - ``SESSION_COOKIE_AGE: 3600``
     - ``DJANGO_SESSION_COOKIE_AGE=3600``
   * - Float
     - ``MY_PACKAGE_SAMPLE_RATE: 0.25``
     - ``DJANGO_MY_PACKAGE_SAMPLE_RATE=0.25``
   * - Boolean
     - ``SESSION_COOKIE_SECURE: true`` (or ``false``)
     - ``DJANGO_SESSION_COOKIE_SECURE=true``: ``1``, ``true``, ``yes`` or ``on`` is true; anything else is
       false
   * - String
     - ``TIME_ZONE: America/Vancouver``. Quote a string that YAML would read as something else:
       ``VERSION_LABEL: "1.10"``, ``ANSWER: "no"``
     - ``DJANGO_TIME_ZONE=America/Vancouver``, used as it is, for a setting whose value is a string
   * - None
     - ``SECURE_PROXY_SSL_HEADER: null``
     - ``DJANGO_SECURE_PROXY_SSL_HEADER=None``
   * - List
     - One ``- item`` per line, or ``[a, b]`` on one line
     - Comma-separated, ``DJANGO_SILENCED_SYSTEM_CHECKS=security.W001,security.W003``, or a JSON or
       Python list
   * - Tuple, or a list of pairs
     - A list: YAML has no tuples, and Django accepts a list wherever it takes a tuple, e.g.
       ``SECURE_PROXY_SSL_HEADER: ["HTTP_X_FORWARDED_PROTO", "https"]``
     - A Python literal: ``DJANGO_SECURE_PROXY_SSL_HEADER='("HTTP_X_FORWARDED_PROTO", "https")'``
   * - Dictionary, nested
     - An indented mapping, e.g. ``LOGGING`` or ``CACHES``, with lists inside it as needed
     - A JSON object, or a Python dict for keys that aren't strings, on one line. The file is easier
   * - A class or a function
     - Its dotted path, as a string: ``TEST_RUNNER: django.test.runner.DiscoverRunner``. Django imports it
     - The same dotted path

``user-settings/settings.example.yaml`` has a worked example of each of these, which a test checks.

A setting that Smarter doesn't define, nor Django, has no value before yours to take a type from. An
environment variable for it is a JSON value, else a Python literal, else a plain string.

Rules
-----

- **A setting's name is upper case**, as Django requires: ``SESSION_COOKIE_AGE``, not
  ``session_cookie_age``. The name of a ``DJANGO_*`` variable is upper-cased for you.
- **Your value replaces Smarter's whole setting.** A dictionary or a list is not merged with Smarter's. To
  change one logger, write the whole ``LOGGING``; to add one cache, write the whole ``CACHES``. Copy
  Smarter's value from ``smarter/settings/`` and edit it.
- **Settings that Smarter computes from other settings are not computed again.** For example, the
  Content Security Policy's sources are built from ``STATIC_URL``, and ``STORAGES`` from whether AWS is
  configured. If you change ``STATIC_URL``, the policy keeps the sources of the old value; change it too.
  One exception follows yours: RedBeat's ``CELERY_REDBEAT_REDIS_URL`` is set to your
  ``CELERY_BROKER_URL`` unless you set it too. The ``CACHES`` that Smarter builds have two caches,
  ``default`` and ``sessions``, on different Redis databases; yours needs both.
- **The secret key is the exception.** ``DJANGO_SECRET_KEY`` is read by ``smarter_settings``, which
  refuses a missing key or a placeholder outside the local environment, before Django starts.
- **Prefer a** ``SMARTER_*`` **setting where one exists.** Many Django settings are derived from
  ``smarter_settings`` (see :doc:`configuration`), e.g. ``ALLOWED_HOSTS`` from ``SMARTER_ALLOWED_HOSTS``,
  and everything derived from it changes with it. Use a user-defined Django setting for what Smarter
  doesn't configure itself.
- **A name that neither Django nor Smarter defines** is set anyway, for a package that reads it, and the
  log warns about it, in case it is a typo.
- **A file or a variable that can't be applied stops Django**, with an error that names it: a file that
  isn't YAML or isn't a mapping, a key that isn't a setting name, or a variable whose value isn't of the
  setting's type, e.g. ``DJANGO_SESSION_COOKIE_AGE=an hour``. In Kubernetes, the pods don't start, and
  ``kubectl logs`` shows the error.
- **Values are never logged.** The log names each setting that you set, never its value, which may be a
  password.

Checking what applied
---------------------

When Django loads its settings, the log has a line for your file and one for your variables, naming each
setting:

.. code-block:: text

   smarter.settings.user.apply_user_settings() Applying 2 setting(s) from /home/smarter_user/user-settings/settings.yaml: ADMINS, SESSION_COOKIE_AGE
   smarter.settings.user.apply_user_settings() Applying 1 setting(s) from DJANGO_* environment variables: AUTHENTICATION_BACKENDS

To see the value that Django runs with, ask Django, in the container or the pod:

.. code-block:: bash

   # locally
   docker exec smarter-api python manage.py diffsettings | grep SESSION_COOKIE_AGE
   # on Kubernetes (prod's namespace, as an example)
   kubectl exec -n smarter-platform-prod deploy/smarter-api -- python manage.py diffsettings | grep SESSION_COOKIE_AGE

Reference
---------

- :mod:`smarter.settings.user`, which reads and applies your settings:
  :doc:`its technical reference </smarter-framework/developer-reference/lib/django/settings/user>`.
- ``user-settings/README.md`` and ``user-settings/settings.example.yaml``, in the repository's root.
- ``env`` in ``helm/charts/smarter/values.yaml``, and ``templates/secret-env.yaml``.
- `Django's settings reference <https://docs.djangoproject.com/en/6.0/ref/settings/>`__, for every
  setting that Django defines.
