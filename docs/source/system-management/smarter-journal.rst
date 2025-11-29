Smarter Journal
================

The Smarter Journal persists all platform http responses to one of a variety of backing services.
It is designed for long term storage of auditable platform data, and is optimized for read performance over write performance.

Enabling the Smarter Journal
----------------------------

The Smarter Journal is enabled from the admin console at run-time from the DJANGO-WAFFLE `Switches` page.
It is not necessary to restart any services when enabling or disabling the journal.

.. raw:: html

   <img src="https://cdn.smarter.sh/images/smarter-waffle-journal.png"
        style="width: 100%; height: auto; display: block; margin: 0 0 1.5em 0; border-radius: 0;"
        alt="Smarter Waffle Switch - Journal"/>

Django Log
----------------

The Smarter platform secondaarily leverages Django Logs for short term archival of platform administration events.
These logs are provided as a convenience for Smarter platform administrators.

**Django Logs are not intended to be a source of auditable platform data** These are routinely purged as part of
normal platform self-maintenance tasks. Additionally, Django Logs are editable and deletable, directly from the
Django Admin console.
