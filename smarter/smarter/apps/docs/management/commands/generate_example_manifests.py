# pylint: disable=W0613
"""This module is used to create a new plugin using manage.py"""

import logging
import os
from typing import Type

from smarter.apps.docs.views.manifest import (
    DocsExampleManifestAccountView,
    DocsExampleManifestApiConnectionView,
    DocsExampleManifestApiKeyView,
    DocsExampleManifestApiView,
    DocsExampleManifestBaseView,
    DocsExampleManifestChatBotView,
    DocsExampleManifestChatHistoryView,
    DocsExampleManifestChatPluginUsageView,
    DocsExampleManifestChatToolCallView,
    DocsExampleManifestChatView,
    DocsExampleManifestPluginView,
    DocsExampleManifestSecretView,
    DocsExampleManifestSqlConnectionView,
    DocsExampleManifestSqlView,
    DocsExampleManifestUserView,
)
from smarter.lib.django.management.base import SmarterCommand


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# pylint: disable=E1101
class Command(SmarterCommand):
    """Django manage.py create_plugin command. This command is used to create a plugin from a yaml import file."""

    def handle(self, *args, **options):
        """
        create example manifest files for every AI resource type

        $ pwd
        /home/smarter_user/smarter
        $ pwd
        /home/smarter_user/smarter
        $ cd ../data/manifests/example_manifests
        $ ls -lha
        total 12K
        drwx------ 1 smarter_user smarter_user 4.0K Dec  5 19:24 .
        drwx------ 1 smarter_user smarter_user 4.0K Dec  5 19:24 ..
        $ pwd
        /home/smarter_user/data/manifests/example_manifests
        $

        """
        self.handle_begin()

        # /home/smarter_user/data/manifests/ is created by Dockerfile
        # and permissions are set so smarter_user can write here.
        output_folder = "/home/smarter_user/data/manifests/example_manifests"

        def write_manifest(view_class: Type[DocsExampleManifestBaseView]):
            """
            Generate example manifest YAML file.
            """
            instance = view_class()
            try:
                response = instance.post(request=None)
            # pylint: disable=broad-except
            except Exception as exc:
                logger.error("Failed to generate manifest for %s: %s", view_class.__name__, exc)
                return

            yaml_content = response.content.decode("utf-8")
            output_path = os.path.join(output_folder, instance.file_name)

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)

        manifests = [
            DocsExampleManifestAccountView,
            DocsExampleManifestApiConnectionView,
            DocsExampleManifestApiView,
            DocsExampleManifestApiKeyView,
            DocsExampleManifestChatView,
            DocsExampleManifestChatHistoryView,
            DocsExampleManifestChatPluginUsageView,
            DocsExampleManifestChatToolCallView,
            DocsExampleManifestChatBotView,
            DocsExampleManifestPluginView,
            DocsExampleManifestSqlConnectionView,
            DocsExampleManifestSqlView,
            DocsExampleManifestUserView,
            DocsExampleManifestSecretView,
        ]
        for manifest_view in manifests:
            write_manifest(manifest_view)
