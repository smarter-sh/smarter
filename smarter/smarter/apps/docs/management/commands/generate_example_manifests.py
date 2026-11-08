"""The ``generate_example_manifests`` command: write an example manifest of every SAM kind, as YAML."""

import os

import yaml

from smarter.apps.api.v1.contract.sam import sam_example, sam_models
from smarter.common.utils import to_snake_case
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

OUTPUT_FOLDER = "/home/smarter_user/data/manifests/example_manifests"
"""Where the manifests are written.

The Dockerfile creates it, and the Helm chart mounts it writable.
"""


class Command(SmarterCommand):
    """
    Write an example manifest of every SAM kind, as YAML, into :data:`OUTPUT_FOLDER`.

    Each is the example that the cli api's ``example-manifest`` view returns, without its read-only
    ``status`` (:func:`smarter.apps.api.v1.contract.sam.sam_example`), in a file named after the kind,
    e.g. ``llm_client.yaml``.
    """

    help = "Write an example manifest of every SAM kind, as YAML, into " + OUTPUT_FOLDER

    def handle(self, *args, **options):
        """Write the manifests.

        A kind whose example fails is logged and skipped.
        """
        self.handle_begin()
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        for kind in sam_models():
            try:
                manifest = sam_example(kind)
            # pylint: disable=broad-except
            except Exception as exc:
                logger.error("%s.handle() failed to make the example manifest of %s: %s", logger_prefix, kind, exc)
                continue
            file_name = to_snake_case(kind) + ".yaml"
            output_path = os.path.join(OUTPUT_FOLDER, file_name)
            with open(output_path, "w", encoding="utf-8") as file:
                yaml.dump(manifest, file, default_flow_style=False)
        self.handle_completed_success()
