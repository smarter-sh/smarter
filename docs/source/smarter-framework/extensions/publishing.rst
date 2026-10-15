Publishing an Extension
=======================

Published Extensions are listed in the Smarter Extension registry, where the administrators of
every Smarter platform can find them, read their documentation, install them with one click, and
be told when they have an update.

The Registry
------------

The registry is a public GitHub repository,
`smarter-sh/extensions-registry <https://github.com/smarter-sh/extensions-registry>`__. It holds
one small YAML file per released version of each Extension, and the list of publishers. Its CI
validates each submission, builds an index of every Extension, signs it with the registry's
Ed25519 key, and publishes it. Platforms verify the signature, and check each archive they download
against the sha256 in the signed index, so an archive can't be swapped after it is published.

Releasing a Version
-------------------

1. **Bump the version** in ``pyproject.toml``, and describe the change in your CHANGELOG.
2. **Test and validate it**: run its tests with ``manage.py test_extension``, and check it with
   ``manage.py validate_extension``. See :doc:`testing`.
3. **Build the archive** with ``manage.py package_extension``, which prints its sha256, and attach
   it to a GitHub release of your repository. The official Extensions' repositories do this with a
   workflow that runs on each ``v*`` tag.
4. **Submit it to the registry**, with a pull request that adds one file,
   ``extensions/<slug>/<version>.yaml``:

   .. code-block:: yaml

       slug: weather
       version: 1.0.0
       publisher: smarter-sh
       archive_url: https://github.com/smarter-sh/smarter-extension-weather/releases/download/v1.0.0/weather-1.0.0.zip
       sha256: 6f1d...

The registry's CI downloads the archive, checks its sha256, and checks that its ``pyproject.toml``'s slug and
version match the file. Once the pull request is merged, the new index is published, and every
platform that has the Extension installed offers the update within a day.

A released version is never changed. To fix one, release another.

Publishers and Trust Badges
---------------------------

Every Extension belongs to a publisher, listed in the registry's ``publishers.yaml``, which only
the Smarter team can change. The first time you publish, add yourself as a publisher in your pull
request. Each publisher has a trust badge, which administrators see before they install:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Badge
     - Who
   * - Official Smarter Extension
     - The Smarter team.
   * - Verified Publisher
     - Organizations and developers that the Smarter team has vetted. Ask the Smarter team, in an
       issue on the registry, to be verified.
   * - Community
     - Everyone else. Their releases are checked by the registry's automation, not reviewed.

Choosing a Slug
---------------

An Extension's slug is permanent: LLMClient manifests list it, and platforms track updates by it.
The registry accepts a slug only from its first publisher. Choose a name that says what the
Extension does, such as ``weather`` or ``date-calculator``, not who made it.

Compatibility
-------------

Set ``requires-smarter`` to the Smarter versions that you have tested. Platforms are offered only
the versions that are compatible with them, so a platform that hasn't upgraded keeps the newest
version that still works with it.
