Smarter Journal
================

The Smarter Journal persists all platform http responses to one of a variety of backing services.
It is designed for long term storage of auditable platform data, and is optimized for read performance over write performance.

Enabling the Smarter Journal
----------------------------

The Smarter Journal is on by default: a new platform's ``enable_journal`` waffle switch is on, so it
keeps an audit trail of every api command and prompt from the start. The web console's dashboard
shows its latest commands, such as apply, deploy and delete, in Recent Activity, and
``GET /api/v1/journal/`` lists its entries. Turn it off, or on again, at run-time in the Django admin's
DJANGO-WAFFLE `Switches` page. It is not necessary to restart any services when enabling or disabling
the journal. ``manage.py initialize_waffle`` creates only the switches that don't exist, so a platform
whose journal was turned off keeps it off.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-waffle-journal.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Waffle Switch - Journal"/>

Django Log
----------------

The Smarter platform secondarily leverages Django Logs for short term archival of platform administration events.
These logs are provided as a convenience for Smarter platform administrators.

**Django Logs are not intended to be a source of auditable platform data** These are routinely purged as part of
normal platform self-maintenance tasks. Additionally, Django Logs are editable and deletable, directly from the
Django Admin console.


Application Logs
----------------

Smarter application logs, while ephemeral in nature, are highly configurable in order to provide real-time, granular
and verbose logging of targeted parts of the application stack. These logs are intended to provide real-time
diagnostics insights into application behavior, and are not intended to be a source of auditable platform data.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/django-admin-waffle-switches.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Django Admin - Waffle Switches"/>

See `Smarter Logging Configuration <../../configuration.html>`_ for details on configuring application logging.
