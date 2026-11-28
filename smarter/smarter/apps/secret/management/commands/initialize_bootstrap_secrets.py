"""
Django manage.py initialize_bootstrap_secrets command: create Smarter Secrets from a folder of files (issue #1099).

Usage::

    python manage.py initialize_bootstrap_secrets [--folder <folder>]

Each file in ``smarter_settings.bootstrap_secrets_dir``, or ``--folder``, becomes the Smarter admin's Secret of the
same name, holding the file's text: e.g. ``openai_api_key``. ``initialize_platform`` runs it before the commands that
create the built-in Providers, search plugins and managed vector databases' connections, which then find their keys
in those Secrets, as every service does. On Kubernetes, the folder is the Kubernetes Secret
``smarter-bootstrap-secrets``, mounted in the init Job only;
locally, the repository's ``bootstrap-secrets/``, mounted in ``smarter-api`` only, at the same path.

A key thus has one source, its Smarter Secret, and never travels as an environment variable. The command needs no
list of names: whatever the folder holds becomes a Secret. Only names are logged, never a value.
"""

import os
from typing import Optional

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.secret.models import Secret
from smarter.common.conf import smarter_settings
from smarter.common.conf.env import is_missing_value
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getSmarterLogger(__name__)

DESCRIPTION = "Created from the platform's bootstrap secrets by manage.py initialize_bootstrap_secrets."
"""The description of a Secret that the command creates.

An existing Secret keeps its own.
"""


def bootstrap_files(folder: str) -> list[str]:
    """
    Name the files in the folder that are Secrets: every regular file whose name doesn't start with a dot.

    A Kubernetes Secret mounted as a volume also holds ``..data`` and a timestamped folder, which hold the files
    that the visible names link to. Those are left out.

    :param folder: The folder.
    :returns: The files' names, sorted. Empty if the folder doesn't exist.
    """
    if not os.path.isdir(folder):
        return []
    names = []
    for name in sorted(os.listdir(folder)):
        if name.startswith("."):
            continue
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        names.append(name)
    return names


def read_value(path: str) -> Optional[str]:
    """
    Return a file's text, without its trailing whitespace, or None if it is empty or a placeholder.

    :param path: The file.
    :returns: The value, or None.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    value = text.strip()
    if not value or is_missing_value(value):
        return None
    return value


class Command(SmarterCommand):
    """Django manage.py initialize_bootstrap_secrets command, which creates or updates the Smarter admin's Secrets."""

    help = "Create or update the Smarter admin's Secrets from a folder of files, one per Secret, named after it."

    def add_arguments(self, parser):
        """
        Add the ``--folder`` option.

        :param parser: The command's argument parser.
        """
        parser.add_argument(
            "--folder",
            default=None,
            help="The folder of files. smarter_settings.bootstrap_secrets_dir by default.",
        )

    def handle(self, *args, **options):
        """
        Create each file's Secret, update one whose value changed, and leave the rest alone.

        :param options: The command's options, ``folder``.
        """
        self.handle_begin()
        folder = options.get("folder") or smarter_settings.bootstrap_secrets_dir
        names = bootstrap_files(folder)
        if not names:
            self.handle_completed_success(msg=f"No bootstrap secrets in {folder}: nothing to create.")
            return
        user_profile = smarter_cached_objects.smarter_admin_user_profile
        created = []
        updated = []
        unchanged = []
        skipped = []
        for name in names:
            value = read_value(os.path.join(folder, name))
            if value is None:
                skipped.append(name)
                continue
            secret = Secret.objects.filter(name=name, user_profile=user_profile).first()
            if secret is None:
                Secret.objects.create(
                    name=name,
                    user_profile=user_profile,
                    description=DESCRIPTION,
                    encrypted_value=Secret.encrypt(value),
                )
                created.append(name)
                continue
            # Fernet gives a new ciphertext each time, so only a changed value is saved: every deploy runs this.
            if secret.get_secret(update_last_accessed=False) == value:
                unchanged.append(name)
                continue
            secret.encrypted_value = Secret.encrypt(value)
            secret.save()
            updated.append(name)
        logger.info(
            "bootstrap secrets from %s: created %s, updated %s, unchanged %s, skipped (empty) %s",
            folder,
            ", ".join(created) or "none",
            ", ".join(updated) or "none",
            ", ".join(unchanged) or "none",
            ", ".join(skipped) or "none",
        )
        self.handle_completed_success(
            msg=f"Bootstrap secrets: {len(created)} created, {len(updated)} updated, {len(unchanged)} unchanged."
        )
