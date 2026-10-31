import logging

from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.llmclient.const import (
    EXAMPLE_MANIFESTS_REPOSITORY_URL,
    STACKADEMY_REPOSITORY_URL,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)


class Command(SmarterCommand):
    """Django manage.py initialize_platform command."""

    def add_arguments(self, parser):
        """Add arguments to the command."""
        parser.add_argument(
            "--username",
            type=str,
            help="The username of the platform's superuser. Default: smarter_settings.admin_username (SMARTER_ADMIN_USERNAME), or 'admin'.",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="The email address of the user to associate with this Secret. If not provided, a default email will be assigned.",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="The password of the superuser and the example users. Default: smarter_settings.admin_password (SMARTER_ADMIN_PASSWORD), or 'smarter' when running locally.",
        )

    # pylint: disable=broad-except
    def handle(self, *args, **options):
        """
        Initialize the Smarter platform.

        Creates the minimal resources necessary to start using Smarter. This is the one place where
        the platform's example resources are created and deployed: the Helm init job and
        ``make docker-init`` run it, and nothing else.

        1. Create the admin user and the example users. The username and password come from
           ``--username`` and ``--password``, or from ``smarter_settings.admin_username`` and
           ``admin_password``, so that the init job passes no password on its command line.
        2. Initialize the Waffle switches, the Smarter project's index, the built-in Providers, the
           official extensions and the vector store providers.
        3. Load the example manifests from GitHub, https://github.com/smarter-sh/example-manifests,
           and deploy their LLMClients. Then delete the example resources whose manifests were removed
           from it since an earlier initialization, with ``delete_retired_examples``.
        4. Load the Stackademy project from GitHub, deploy its LLMClients, and verify them.
        5. Verify the DNS configuration, and sync the ledger of infrastructure resources with the
           Kubernetes cluster.

        Deploying an LLMClient creates its DNS record and Kubernetes ingress, so the LLMClients are
        deployed everywhere except in the local environment, where they are only applied.
        """
        self.handle_begin()

        username = options.get("username") or smarter_settings.admin_username

        email = options.get("email")
        if not email:
            email = f"{username}@{smarter_settings.root_domain}"
            self.stdout.write(f"No email was given for the admin user {username}. Using {email}.")

        password = options.get("password")
        if not password and smarter_settings.admin_password:
            password = smarter_settings.admin_password.get_secret_value()
        if not password:
            if smarter_settings.environment != SmarterEnvironments.LOCAL:
                raise CommandError(
                    "An administrator password is required outside the local environment: "
                    "set SMARTER_ADMIN_PASSWORD, or pass --password."
                )
            password = "smarter"
            self.stdout.write(self.style.WARNING(f"No password provided, using the default value: {password}"))
        deploy = smarter_settings.environment != SmarterEnvironments.LOCAL

        # create Smarter Account and admin User.
        # ---------------------------------------------------------------------
        call_command("create_smarter_admin", username=username, password=password, email=email)
        call_command(
            "create_user",
            account_number=SMARTER_ACCOUNT_NUMBER,
            username="staff_user",
            email=f"staff@{smarter_settings.root_domain}",
            password=password,
            first_name="Staff",
            last_name="User",
            admin=True,
        )
        call_command(
            "create_user",
            account_number=SMARTER_ACCOUNT_NUMBER,
            username="customer_user",
            email=f"customer@{smarter_settings.root_domain}",
            password=password,
            first_name="Customer",
            last_name="User",
        )

        # Initialize Smarter platform components. A failure of most steps is logged, and the next step
        # runs. A failure in ``fatal`` is also logged, and makes this command exit with code 1 once every
        # step has run, so that the init job fails.
        # ---------------------------------------------------------------------
        fatal: list[str] = []

        try:
            call_command("initialize_waffle")  # Initialize builtin Waffle switches for feature flagging
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize Waffle switches: %s", e)

        try:
            # queued for the Celery worker, which downloads the repositories from GitHub: the
            # smarter_project_* MCPClients of example-manifests read them through the platform's MCP server.
            call_command("index_smarter_project", queue=True)
        except (Exception, SystemExit) as e:
            logger.error("Failed to queue the indexing of The Smarter Project's repositories: %s", e)

        try:
            call_command("initialize_providers")  # Initialize builtin LLM providers: openai, metaai, googleia
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize providers: %s", e)

        try:
            # after initialize_providers, whose Secrets, e.g. google_maps_api_key, configure the extensions.
            # Before the example manifests, whose LLMClients list the official extensions.
            call_command("install_official_extensions")
        except (Exception, SystemExit) as e:
            # fatal: the example LLMClients that use a missing official extension are skipped.
            logger.error("Failed to install the official extensions: %s", e)
            fatal.append("install_official_extensions")

        try:
            call_command("initialize_vectorstore_providers")  # Initialize builtin vectorstore providers: pinecone
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize vectorstore providers: %s", e)

        try:
            # The example manifests: the community-supported collection of every kind's examples, in their
            # own repository, which load_from_github applies in the order of their dependencies. After
            # initialize_providers, install_official_extensions and initialize_vectorstore_providers: its
            # Proxies, Guardrails and LLMClients name the built-in Providers and their Secrets, its
            # LLMClients the official extensions, and its Vectorstores the managed services' ApiConnections.
            # The Smarter admin owns them, so every account may use them, and each account also gets its own
            # copy of the plugins and LLMClients from initialize_account. Its LLMClients are deployed outside
            # the local environment. Its CustomDomain, example.com, is applied, not verified. Its Budgets
            # attach to nothing: each is created once, detached, and left as it is afterwards. A manifest
            # that names a resource that this platform doesn't have, e.g. an MCPClient whose Secret of a
            # third-party service no one has created, is skipped until it does. One that fails doesn't stop
            # the others.
            call_command(
                "load_from_github",
                url=EXAMPLE_MANIFESTS_REPOSITORY_URL,
                account_number=SMARTER_ACCOUNT_NUMBER,
                username=username,
                deploy=deploy,
                run_scripts=True,
                skip_missing_references=True,
            )
        except (Exception, SystemExit) as e:
            logger.error("Failed to load the example manifests from %s: %s", EXAMPLE_MANIFESTS_REPOSITORY_URL, e)

        try:
            # after the example manifests. load_from_github never deletes a resource whose manifest was removed
            # from its repository, e.g. the MCPClient of an MCP server endpoint that no longer exists, which
            # then fails every time it is used. This deletes those that the Smarter admin owns.
            call_command("delete_retired_examples", username=username)
        except (Exception, SystemExit) as e:
            logger.error("Failed to delete the retired example resources: %s", e)

        try:
            # The Stackademy project: the Secrets, Connections, plugins, LLMClients and Budget of a fictional
            # code academy, in their own repository, which load_from_github applies in the order of their
            # dependencies. After initialize_providers: its plugins and LLMClients use the openai Provider.
            # Its LLMClients are deployed as they are applied, outside the local environment. Its
            # ApiConnection's Secret is also the password of this platform's Stackademy course catalogue,
            # /api/v1/demos/stackademy/course-catalogue/. run_scripts runs the scripts that the repository's
            # scripts/scripts.yaml lists, before and after its manifests: Stackademy's pre script creates its
            # course database, smarter_test_db, and its read-only users, which its SqlConnection connects to, as
            # SMARTER_MYSQL_ROOT_USERNAME. Only here: initialize_account loads each account's copy of the
            # manifests without running the scripts again.
            call_command(
                "load_from_github",
                url=STACKADEMY_REPOSITORY_URL,
                account_number=SMARTER_ACCOUNT_NUMBER,
                username=username,
                deploy=deploy,
                run_scripts=True,
            )
        except (Exception, SystemExit) as e:
            logger.error("Failed to load the Stackademy project from %s: %s", STACKADEMY_REPOSITORY_URL, e)
            fatal.append("load_from_github")

        try:
            # after load_from_github. It prompts the Stackademy LLMClients, and exits when they don't work.
            call_command("verify_stackademy", account_number=SMARTER_ACCOUNT_NUMBER)
        except (Exception, SystemExit) as e:
            logger.error("The Stackademy LLMClients don't work: %s", e)

        try:
            call_command(
                "verify_dns_configuration"
            )  # if AWS is configured then Verify Route53 Hosted Zones and DNS records
        except (Exception, SystemExit) as e:
            logger.error("Failed to verify DNS configuration: %s", e)

        try:
            # read-only: record the Kubernetes cluster's resources in the ledger now, rather than
            # 15 minutes later when Celery Beat first runs it. It exits on failure, e.g. no cluster.
            call_command("sync_infrastructure_inventory")
        except (Exception, SystemExit) as e:
            logger.error("Failed to sync the infrastructure inventory: %s", e)

        if fatal:
            raise CommandError(f"initialize_platform completed, but these steps failed: {', '.join(fatal)}")
        self.handle_completed_success()
