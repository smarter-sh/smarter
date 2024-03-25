# -*- coding: utf-8 -*-
"""
Import celery, load its settings from the django settings
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


# Set the default Django settings module for the 'celery' program
# and then instantiate the Celery singleton.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

# pylint: disable=wrong-import-position,unused-import
from smarter.lib.celery_conf import APP as celery_app


__all__ = ("celery_app",)
