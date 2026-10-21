"""Write an LLMClient's architecture, the tree of the SAM resources that it is built from, as JSON."""

import json
from pathlib import Path

from django.core.management.base import CommandError
from django.test import RequestFactory

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.models import LLMClient
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.manifest.models import SAMDependencyTreeNode
from smarter.lib.typing import SmarterDictType


def public_tree(node: SAMDependencyTreeNode) -> SAMDependencyTreeNode:
    """
    Copy a tree for a public web page, without its owners or web console urls.

    smarter.sh shows the architectures of the platform's built-in LLMClients. The owners are people's
    names, and the urls are web console pages that need a login.

    :param node: The tree's root.
    :type node: SAMDependencyTreeNode
    :returns: The tree, with every node's owner and url set to ``None``.
    :rtype: SAMDependencyTreeNode
    """
    return node.model_copy(
        update={"owner": None, "url": None, "children": [public_tree(child) for child in node.children]}
    )


class Command(SmarterCommand):
    """Django manage.py export_llmclient_architecture command."""

    help = (
        "Write an LLMClient's architecture, the tree of the SAM resources that it is built from, as the web "
        "console's Architecture tab receives it, as JSON. --public leaves out the owners and the web console "
        "urls, for a public web page such as smarter.sh's."
    )

    def add_arguments(self, parser):
        parser.add_argument("--name", type=str, required=True, help="The LLMClient's name, e.g. math.")
        parser.add_argument(
            "--account_number",
            type=str,
            default=SMARTER_ACCOUNT_NUMBER,
            help=f"The account of the LLMClient. Default: {SMARTER_ACCOUNT_NUMBER}, the Smarter account.",
        )
        parser.add_argument("--public", action="store_true", help="Leave out the owners and the web console urls.")
        parser.add_argument("--output", type=str, default=None, help="A file to write. Default: standard output.")

    def handle(self, *args, **options):
        self.handle_begin()
        name = options["name"]
        account_number = options["account_number"]
        llmclient = LLMClient.objects.filter(name=name, user_profile__account__account_number=account_number).first()
        if llmclient is None:
            raise CommandError(f"No LLMClient {name} in account {account_number}.")

        # the tree is the one that the LLMClient's owner sees, who may read every resource of it.
        request = RequestFactory().get("/")
        request.user = llmclient.user_profile.user
        kind = SAMKinds.LLM_CLIENT.value
        broker = SAMLLMClientBroker(request, name=llmclient.name, kind=kind)
        tree = broker.dependency_tree_node(kind, llmclient, ancestors=frozenset())
        if options["public"]:
            tree = public_tree(tree)

        data: SmarterDictType = tree.model_dump(mode="json")
        text = json.dumps(data, indent=2) + "\n"
        if options["output"]:
            Path(options["output"]).write_text(text, encoding="utf-8")
            self.stdout.write(options["output"])
        else:
            self.stdout.write(text)
        self.handle_completed_success()
