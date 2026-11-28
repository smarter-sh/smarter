"""
Import celery, load its settings from the django settings.

and auto discover tasks in all installed django apps.

Taken from: https://celery.readthedocs.org/en/latest/django/first-steps-with-django.html

NOTE: the official documentation suggests naming this file celery.py, but that
causes a circular reference with the celery package itself because of how the smarter
package is added to the Docker file system. The short story is that Python doesn't distinguish
between the celery PyPi package and the smarter module because of the PYTHONPATH.
Both resolve to just 'celery', and so it tries to import the package instead
of the module. Thus, we have to name it something else.
"""

import os

from smarter.common.conf import smarter_settings

# Set the default Django settings module for the 'celery' program, and then instantiate the Celery
# singleton: importing the Celery app reads the Django settings, so the import must follow. The default is
# the module of the environment that smarter_settings name (SMARTER_ENVIRONMENT), as manage.py, asgi.py and
# wsgi.py choose it, so that a worker needs no DJANGO_SETTINGS_MODULE of its own. One that is set still wins.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings." + smarter_settings.environment)

# pylint: disable=wrong-import-position,unused-import
from smarter.lib.celery_conf import APP as app  # noqa: E402

__all__ = ("app",)
