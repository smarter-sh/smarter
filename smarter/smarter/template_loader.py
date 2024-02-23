# -*- coding: utf-8 -*-
"""ReactJS integration with Django."""

import os

from django.apps import apps
from django.template.loaders.filesystem import Loader as FilesystemLoader


class ReactAppLoader(FilesystemLoader):
    """A custom template loader that includes each django app's reactapp/dist directory in the search path."""

    def get_dirs(self):

        dirs = super().get_dirs()
        for app in apps.get_app_configs():
            dirs.append(os.path.join(app.path, "reactapp", "dist"))
        return dirs
