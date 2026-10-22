import logging

from django.core.management import call_command
from django.core.management.base import CommandError

from smarter.apps.llmclient.const import STACKADEMY_REPOSITORY_URL
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
        2. Initialize the Waffle switches, then add the example resources: Guardrails, CustomDomains,
           Budgets, MCPClients, the Smarter project's index, LLMHosts, Providers and their built-in
           Proxies, extensions, vector stores, tools and LLMClients.
        3. Deploy the example LLMClients.
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
            self.stdout.write(
                self.style.WARNING(f"No email provided, assigning a default email for this Secret: {email}")
            )

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
            call_command("add_example_guardrails")
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize Guardrails: %s", e)

        try:
            # applied, not deployed: an example CustomDomain, whose verification fails.
            call_command("add_example_custom_domains")
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize CustomDomains: %s", e)

        try:
            call_command("add_example_budgets")  # Detached budgets, which superusers can attach to resources
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize Budgets: %s", e)

        try:
            call_command("add_example_mcpclients")
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize MCPClients: %s", e)

        try:
            # queued for the Celery worker, which downloads the repositories from GitHub: the
            # built-in smarter_project_* MCPClients read them through the platform's MCP server.
            call_command("index_smarter_project", queue=True)
        except (Exception, SystemExit) as e:
            logger.error("Failed to queue the indexing of The Smarter Project's repositories: %s", e)

        try:
            call_command("add_example_llmhost_compute")
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize LLMHostCompute: %s", e)

        try:
            # after LLMHostCompute: each built-in LLMHost's spec.compute must exist.
            call_command("add_example_llmhost")
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize LLMHosts: %s", e)

        try:
            call_command("initialize_providers")  # Initialize builtin LLM providers: openai, metaai, googleia
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize providers: %s", e)

        try:
            # after initialize_providers, whose Secrets, e.g. google_maps_api_key, configure the extensions.
            # Before add_example_llmclients, whose example LLMClients list the official extensions.
            call_command("add_example_extensions")
        except (Exception, SystemExit) as e:
            # fatal: the example LLMClients that use a missing official extension are skipped.
            logger.error("Failed to install the official extensions: %s", e)
            fatal.append("add_example_extensions")

        try:
            # after initialize_providers: each built-in Proxy's Provider and API key Secret must exist.
            call_command("add_example_proxies")
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize Proxies: %s", e)

        try:
            call_command("initialize_vectorstore_providers")  # Initialize builtin vectorstore providers: pinecone
        except (Exception, SystemExit) as e:
            logger.error("Failed to initialize vectorstore providers: %s", e)

        try:
            call_command("add_example_vectorstores")  # Applied, not deployed: example vector databases
        except (Exception, SystemExit) as e:
            logger.error("Failed to apply the example vectorstores: %s", e)

        try:
            call_command("add_example_tools", username=username)
        except (Exception, SystemExit) as e:
            logger.error("Failed to apply the example tools: %s", e)

        try:
            # last of the examples: the example LLMClients use the Providers, the official extensions,
            # the MCPClients, the tools and the Guardrails.
            call_command("add_example_llmclients", username=username)
        except (Exception, SystemExit) as e:
            logger.error("Failed to apply the example LLMClients: %s", e)

        if deploy:
            try:
                call_command("deploy_example_llmclients", account_number=SMARTER_ACCOUNT_NUMBER)
            except (Exception, SystemExit) as e:
                logger.error("Failed to deploy the example LLMClients: %s", e)
                fatal.append("deploy_example_llmclients")

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
