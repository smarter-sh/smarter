Managing Extensions
===================

Extensions are Python packages that add tools to the LLMs of a Smarter platform. Platform
superusers install them at run time, from the web console's **Extensions** page, without a
redeploy, and every account's LLMClients can then list them in their manifests'
``spec.extensions``. See :doc:`../smarter-framework/extensibility` for how Extensions differ from
Plugins, and :doc:`../smarter-framework/smarter-extensions` for how to build one.

.. warning::

   An Extension's code runs inside the platform, with the same access as Smarter's own code: its
   database, its Secrets, and its cloud credentials. Smarter does not sandbox it. Install only
   Extensions whose source you have reviewed, or whose publisher you trust. The registry's trust
   badges, described below, tell you who published an Extension and whether the Smarter team has
   vetted them.

Only superusers can manage Extensions. Account administrators choose which of their LLMClients
use the Extensions that are available to their account.

The Extensions Page
-------------------

In the web console, click **Extensions** in the sidebar's **Tools** section (``/extensions/``).
Every user sees it. A superuser manages Extensions there, and the link shows them a count of the
Extensions that have an update available. Everyone else sees the page read-only: the Extensions
that their account may use, and the registry, with no buttons, switches or install actions. An
Extension's page shows them its overview, tools, versions and resources, but not its settings,
its availability, or who installed each version. The page has two tabs.

**Installed** lists the installed Extensions:

- **Version**: the version that runs, and a newer, compatible version that the registry offers,
  if any.
- **Trust**: the publisher's badge: *Official Smarter Extension*, *Verified Publisher*,
  *Community*, or *Unverified* for an uploaded archive.
- **Source**: the Smarter Extension registry, or an uploaded archive.
- **Enabled**: whether LLMs are offered its tools. The switch enables or disables it.
- **Error**: whether the last lifecycle step or load failed. Open the Extension to read the error.

Click an Extension's name to open its page. The buttons at the top of the page upload an archive,
and check the registry for updates.

The Django admin console's **LLMTool** › **Extensions** page lists the same Extensions,
read-only, with a **Manage in the console** link to each one's page.

Every user, superuser or not, sees the Extensions that their account may use on the
**Extensions** tab of the web console's **LLMTools** page (``/llm-tools/``), beside their own and
shared Tool Plugins. The tab is read-only for everyone: it lists each Extension's name, slug,
version, publisher, description, whether it is enabled, its trust badge and its source, so that
a prompt engineer knows which slugs an LLMClient's ``spec.extensions`` may list. A disabled
Extension is listed too, because an LLMClient may list it: its tools are offered once a
superuser enables it.

Installing from the Registry
----------------------------

**Browse the registry** lists every Extension in the Smarter Extension registry. Search them by
name, description or publisher, or filter by trust badge. Each card shows the newest version that
is compatible with your platform's Smarter version, and whether it is installed. **Details** shows
an Extension's documentation and its versions before you install it, and installs a version that
you choose.

**Install** downloads the archive, checks it against the sha256 in the registry's signed index,
and installs it:

1. Smarter checks that the Extension is compatible: its Python version, its Smarter version, and
   that every library it needs is installed on the platform. Extensions cannot install libraries.
2. It imports the Extension's code, which proves that it loads, before anything is saved.
3. It saves the version, creates the Extension's waffle switches, applies the SAM resources that
   it ships, and runs its install hooks.

A new Extension is installed **disabled**, and its page opens: configure its settings, then enable
it.

The registry's index is signed. Smarter verifies the signature with the registry's public key,
and refuses an index that doesn't match. Until the key is configured, the registry is disabled and
Extensions can only be uploaded. See `Configuring the Registry`_.

Trust Badges
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Badge
     - Meaning
   * - Official Smarter Extension
     - Published by the Smarter team.
   * - Verified Publisher
     - Published by an organization or developer that the Smarter team has vetted.
   * - Community
     - Published to the registry by anyone else. Its release was checked by the registry's
       automation, not reviewed by the Smarter team.
   * - Unverified
     - Uploaded to this platform, not installed from the registry.

Uploading an Extension
----------------------

**Upload extension** installs a ``.zip`` archive from your computer, of at most 10 MB, for example
an Extension that your own team built, or one that isn't in the registry. An uploaded Extension is
badged *Unverified*, and is never updated from the registry, so that it can't be replaced by a
registry package that happens to have the same slug.

An Extension's Page
-------------------

An Extension's page (``/extensions/<slug>/``) shows its name, trust badge, version and state, with
its **Enable** or **Disable** button, and any error. Its tabs:

- **Overview**: its publisher, source, license, homepage, and documentation.
- **Tools**: its tools, by the names that the LLM sees (``ext_<slug>_<tool>``), with their
  descriptions and parameters.
- **Settings**: the form of its settings. See `Configuring an Extension`_.
- **Availability**: which accounts may use it. See `Availability`_.
- **Versions**: every version that was installed. See `Rolling Back`_.
- **Resources**: the SAM resources that it created, and its waffle switches
  (``ext_<slug>_<name>``), with whether each is on. Turn them on and off in **Django Waffle** ›
  **Switches**.

Configuring an Extension
~~~~~~~~~~~~~~~~~~~~~~~~

The **Settings** form is generated from the settings that the Extension declares. A setting may
have a default, which an empty field restores, and a required setting must have a value before
the Extension can be enabled. The page lists the required settings that are missing.

A secret setting, such as an API key, is stored in a :doc:`Secret <../smarter-resources/smarter-secret>`.
The form shows whether it is set, and the name of its Secret, never its value. Keep it, type a new
value, which Smarter saves in a Secret named ``extension_<slug>_<setting>``, choose one of the
platform administrator's Secrets, or clear it. Secret values are encrypted at rest, and are never
shown again.

Availability
~~~~~~~~~~~~

By default, every account may use an Extension. To restrict it, choose **Only these accounts may
use it**, select the accounts, and click **Save availability**. An LLMClient whose account may not
use an Extension can't list it, and an LLMClient that already lists it no longer offers its tools.

Enabling and Disabling
----------------------

**Enable** offers the Extension's tools to the LLMs of every LLMClient that lists it, from the
next prompt, in every pod. **Disable** withdraws them, just as quickly, which makes it the
Extension's kill switch. LLMClients that list a disabled Extension keep working without its tools,
and their chat shows that it is disabled. Both are on the Extension's page, and on the switch in
its row of the **Installed** tab.

Updates
-------

Like WordPress, Smarter knows when an update is available. Celery beat checks the registry once a
day, and records the newest compatible version of each Extension installed from the registry.
**Check for updates** on the Extensions page checks immediately.

When an update is available, the Extension's page says so, with an **Update to** button. An update
runs the new version's upgrade hooks, keeps its settings and its enabled state, applies the SAM
resources that the new version ships, and deletes those it no longer ships. If the new version
needs a setting that isn't configured, the Extension is disabled until it is.

Rolling Back
~~~~~~~~~~~~

Every version that was installed is kept. The **Versions** tab lists them, each earlier one with a
**Roll back to** button, which makes that version the one that runs again.

Uninstalling an Extension
-------------------------

**Uninstall**, at the bottom of the Extension's page, asks you to confirm, then runs its uninstall
hooks, deletes the SAM resources and waffle switches that it created, its settings and its
versions, and removes it from every LLMClient that lists it. The Secrets of its secret settings
are kept.

When Something Goes Wrong
-------------------------

- **The install is refused**: the message says why, for example a library the platform doesn't
  have, or an incompatible Smarter version. Nothing was saved.
- **The Extension was installed, but disabled, with an error**: a step after the install failed,
  for example a SAM resource that it ships, or its install hook. Read the error on its page.
- **A tool call fails**: the LLM is told what went wrong, and the chat goes on. The Extension's
  log messages start with ``smarter_extensions.<slug>``, and are switched on by the
  ``log_extension`` waffle switch.
- **The Extension's code no longer loads**, for example after a platform upgrade removed a library
  that it needs: its tools are skipped, and each chat says why. It can still be uninstalled.

Configuring the Registry
------------------------

Two settings, in your environment or Helm values, configure the registry:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Setting
     - Meaning
   * - ``SMARTER_EXTENSION_REGISTRY_URL``
     - The url of the registry's signed index. The default is the Smarter Extension registry,
       ``https://smarter-sh.github.io/extensions-registry/index.json``.
   * - ``SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY``
     - The registry's Ed25519 public key, base64, which verifies the index's signature. It is
       public, not a secret. While it is empty, the registry is disabled.

An organization can run its own registry, for example of its internal Extensions, by publishing a
signed index in the same format, and setting both values.

Management Commands
-------------------

Each action is also a management command, for scripts and automation:

.. code-block:: console

    python manage.py install_extension --registry weather          # install or update from the registry
    python manage.py install_extension weather-1.0.0.zip --enable  # install an archive, and enable it
    python manage.py uninstall_extension weather
    python manage.py add_example_extensions                        # install the official Extensions

``manage.py initialize_platform`` runs ``add_example_extensions``, which installs the official
Extensions, *calculator*, *date-calculator* and *weather*, from the registry, configures their
secret settings from the platform's Secrets of the same names, for example the weather
Extension's ``google_maps_api_key``, and enables them. While the registry is disabled, it installs
nothing, and the built-in LLMClients that list these Extensions are skipped until they are
installed.
