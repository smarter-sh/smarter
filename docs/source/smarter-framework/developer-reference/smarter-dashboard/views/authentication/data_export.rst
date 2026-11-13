Dashboard Authentication - Download My Data
=============================================

**Download My Data**, in the user menu, gives a user a copy of everything that they've built on the
platform: the manifest of every resource that they own, in every account that they belong to, zipped
into one file, and emailed to them as a link that works for 24 hours.

It opens a dialog that first explains what is about to happen: what the zip file holds, that it usually
takes a few seconds, where the link is emailed and for how long it works, and that Secrets' values are
left out. **Request my data** starts an export, and the dialog then follows it, step by step, with an
illustration of each one:

1. **Find your resources**: every resource that the user owns, from every list of the web console, with
   each list's own queryset (:func:`smarter.lib.django.listview.listview_registry`), so that the export
   holds what the user's lists show them as theirs.
2. **Write their manifests**: each resource's manifest, as ``smarter describe`` returns it
   (:func:`smarter.apps.dashboard.resource_detail.manifest_data`), one YAML file per resource, at
   ``<account number>/<kind>/<name>.yaml``. The dialog counts them as they are written.
3. **Zip them up**: the manifests, and a README that says what the zip file holds and how to apply a
   manifest again, in one zip file. A resource that can't be described, e.g. because it is broken, is
   named in the README, with the reason, rather than failing the export.
4. **Store the zip file privately**: in the environment's private storage, ``infrastructure.storage``
   (see :doc:`/smarter-framework/technologies/infrastructure`), never in its public bucket.
5. **Email you a link**: a presigned url to the zip file, which expires after 24 hours. The admin gets no
   blind copy, because the link is the only key to the file.

A Secret's value is replaced by a placeholder, because the link travels by email, and an email can be
forwarded. Its name, description and other settings are kept, so that its manifest can be applied again
once its value is set. Other resources refer to Secrets by name, and their manifests hold no credentials.

The user can close the dialog at any time: the export runs in the Celery task
:func:`smarter.apps.account.tasks.create_data_export`, and the email comes anyway. Opening the dialog
again while an export runs follows it from where it is. A user may start five exports a day. Each one is
recorded in a :class:`~smarter.apps.account.models.DataExport`, which the Django admin lists, read-only,
as a record of who exported their data, and when. Private storage deletes each zip file a day after it
was saved, and the Celery Beat task :func:`smarter.apps.account.tasks.delete_expired_data_exports`
deletes any whose link has expired, every six hours.

The dialog calls the console's account api: ``GET /api/web/account/data-export/`` for what it says before
the user starts, ``POST`` to start an export, and ``GET /api/web/account/data-export/<id>/`` for an
export's progress. See :doc:`../../../web-console-api`.

A program does the same with an api key, through the REST api, as the Smarter SDKs do:
``GET /api/v1/accounts/data-exports/`` for the overview, ``POST`` to start an export (``202`` when it
starts, ``200`` with the export that is already in progress, ``429`` when the user may not start one
now), and ``GET /api/v1/accounts/data-exports/<id>/`` for its progress. The link is still emailed to
the user, never returned in a response. See :doc:`/smarter-framework/smarter-api/api-contract`.

.. automodule:: smarter.apps.account.data_export
    :members:
    :show-inheritance:

.. automodule:: smarter.apps.account.models.data_export
    :members:
    :show-inheritance:
    :no-index:

.. automodule:: smarter.apps.account.api.web.data_export
    :members:
    :show-inheritance:

.. automodule:: smarter.apps.account.api.v1.views.data_export
    :members:
    :show-inheritance:
