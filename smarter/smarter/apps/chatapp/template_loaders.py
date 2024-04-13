"""ReactJS integration with Django."""

import os

from django.apps import apps
from django.template.loaders.filesystem import Loader as FilesystemLoader


class ReactAppLoader(FilesystemLoader):
    """A custom template loader that includes each django app's reactapp/dist directory in the search path."""

    _dirs_cache = None

    def get_dirs(self):
        if self._dirs_cache is not None:
            return self._dirs_cache

        self._dirs_cache = super().get_dirs()
        for app in apps.get_app_configs():
            path = os.path.join(app.path, "reactapp", "dist")
            if os.path.exists(path):
                self._dirs_cache.append(path)
        return self._dirs_cache
