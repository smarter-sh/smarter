"""Apply the example LLMClient manifests, e.g. the ``smarter`` LLMClient."""

import copy
import glob
import os
from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.llmclient.const import EXAMPLE_LLMCLIENTS_PATH
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import Extension
from smarter.lib import json
from smarter.lib.django.management.examples import SmarterExamplesCommand
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.typing import SmarterDictType


class Command(SmarterExamplesCommand):
    """
    Django manage.py add_example_llmclients command.

    Applies the LLMClient manifests in smarter/apps/llmclient/data/llm-clients, e.g. the ``smarter``
    LLMClient. It creates them, and deploys nothing: ``manage.py deploy_example_llmclients`` deploys
    them. The Stackademy LLMClients are not among them: ``manage.py load_from_github`` applies them,
    from the smarter-sh/stackademy repository.

    An LLMClient that exists keeps its ``deployed`` value. A manifest is not deployed, so applying
    it as it is would undeploy an LLMClient that is deployed, whose undeploy task destroys its
    A record, only for the next deploy to create it again. Resolvers that query the domain in
    between cache the NXDOMAIN for minutes.

    An LLMClient that needs an extension that is not installed is skipped, with a warning:
    extensions are installed by ``manage.py add_example_extensions``, from a registry that may not
    be reachable yet. Run it after the commands that create what the LLMClients use: the Providers,
    extensions, MCPClients, tools and Connections.
    """

    help = (
        "Apply the example LLMClient manifests, in smarter/apps/llmclient/data/llm-clients. "
        "Nothing is deployed: deploy_example_llmclients does."
    )
    family = "LLMClient"

    def add_examples(self, user_profile: Optional[UserProfile]) -> list[str]:
        """Apply each LLMClient, with the ``deployed`` value of the LLMClient that exists, if any."""
        filespecs = sorted(glob.glob(os.path.join(EXAMPLE_LLMCLIENTS_PATH, "*.yaml")))
        failed = []
        for filespec in filespecs:
            manifest = SAMLoader(file_path=filespec).json_data or {}
            missing = self.missing_extensions(manifest.get("spec", {}).get("extensions") or [])
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped {os.path.basename(filespec)}: it needs extensions that are not installed: "
                        f"{', '.join(missing)}. Run add_example_extensions, then this command again."
                    )
                )
                continue
            manifest = self.keep_deployed(manifest, user_profile)  # type: ignore[arg-type]
            error = self.apply(filespec, user_profile, manifest=json.dumps(manifest))  # type: ignore[arg-type]
            if error:
                failed.append(error)
            else:
                self.stdout.write(f"Applied {os.path.basename(filespec)}.")
        return failed

    @staticmethod
    def keep_deployed(manifest: SmarterDictType, user_profile: UserProfile) -> SmarterDictType:
        """
        Return a copy of an LLMClient manifest whose ``deployed`` is that of the LLMClient that exists, if any.

        A manifest is not deployed, so applying it as it is would undeploy an LLMClient that is
        deployed. ``manage.py load_from_github`` applies LLMClients with it too.

        :param manifest: The LLMClient manifest.
        :param user_profile: The owner of the LLMClient.
        :returns: The manifest, with ``spec.config.prompt.deployed`` set.
        :rtype: SmarterDictType
        """
        manifest = copy.deepcopy(manifest)
        name = manifest.get("metadata", {}).get("name")
        deployed = LLMClient.objects.filter(user_profile=user_profile, name=name, deployed=True).exists()
        manifest.setdefault("spec", {}).setdefault("config", {}).setdefault("prompt", {})["deployed"] = deployed
        return manifest

    @staticmethod
    def missing_extensions(slugs: list[str]) -> list[str]:
        """
        Return the slugs, of those that an LLMClient manifest lists, of the extensions that are not installed.

        :param slugs: The extensions that the manifest lists.
        :returns: Those that are not installed.
        :rtype: list[str]
        """
        installed = set(
            Extension.objects.filter(slug__in=slugs, installed_version__isnull=False).values_list("slug", flat=True)
        )
        return [slug for slug in slugs if slug not in installed]
