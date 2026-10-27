"""Verify that the Stackademy LLMClients work, with a real prompt to each one."""

from http import HTTPStatus

from django.core.management import CommandError
from pydantic import ValidationError
from rest_framework.test import APIClient

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.models import (
    PromptChatApiMessage,
    PromptChatApiPromptResponse,
)
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_ACCOUNT_NUMBER, SmarterEnvironments
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import json, logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)
logger_prefix = SmarterFormattedText.text(f"{__name__}")

STACKADEMY_LLMCLIENTS = ("stackademy_sql", "stackademy_api")
"""The Stackademy LLMClients, in :data:`~smarter.apps.llmclient.const.STACKADEMY_REPOSITORY_URL`."""

VERIFICATION_PROMPT = "Do you offer any courses on AI?"
"""The prompt that each Stackademy LLMClient must answer with its plugin's course catalogue data."""


class Command(SmarterCommand):
    """
    Django manage.py verify_stackademy command.

    Verifies that the Stackademy LLMClients of an account work: it sends each one a real, billable
    prompt, through the chat api, and fails unless the LLM called the LLMClient's plugin, the
    plugin returned course catalogue data, and the LLM answered. It creates nothing.

    The Stackademy resources are the manifests of the Stackademy project,
    https://github.com/smarter-sh/stackademy, which ``manage.py load_from_github`` applies:
    ``manage.py initialize_platform`` loads it for the Smarter admin, then runs this command.
    The platform provides what they query: the Stackademy test database, and the course catalogue.

    - ``stackademy_sql``: its SqlPlugin queries the Stackademy test database, with a SqlConnection.
    - ``stackademy_api``: its ApiPlugin queries this platform's Stackademy course catalogue,
      ``/api/v1/demos/stackademy/course-catalogue/``, with an ApiConnection.
    """

    help = (
        "Verify that the Stackademy LLMClients work, with a real, billable prompt to each one. "
        "Load https://github.com/smarter-sh/stackademy with load_from_github first."
    )

    def add_arguments(self, parser):
        """Add arguments to the command."""

        parser.add_argument(
            "--account_number",
            type=str,
            help="The account whose admin owns the Stackademy LLMClients. Defaults to the Smarter account.",
            default=SMARTER_ACCOUNT_NUMBER,
        )

    def handle(self, *args, **options):
        """Verify the Stackademy LLMClients."""
        self.handle_begin()

        account_number = options.get("account_number")
        if not account_number:
            logger.error("%s account number is required.", logger_prefix)
            self.handle_completed_failure(msg="account number is required.")
            return
        try:
            account = Account.get_cached_object(invalidate=False, account_number=account_number)
        except Account.DoesNotExist:
            account = None
        if not account:
            logger.error("%s Account with account number %s does not exist.", logger_prefix, account_number)
            self.handle_completed_failure(msg=f"Account with account number {account_number} does not exist.")
            return
        admin_user = get_cached_admin_user_for_account(account=account)
        if not admin_user:
            logger.error("%s No admin user found for account %s.", logger_prefix, account_number)
            self.handle_completed_failure(msg=f"No admin user found for account {account_number}.")
            return

        try:
            user_profile = UserProfile.get_cached_object(account=account, user=admin_user)
            self.verify_llmclients(user_profile=user_profile)
        # pylint: disable=W0718
        except Exception as e:
            self.handle_completed_failure(e)
            return

        self.handle_completed_success()

    def verify_llmclients(self, user_profile: UserProfile) -> None:
        """
        Verify that each of the Stackademy LLMClients works, with a single-use api key.

        :param user_profile: The owner of the Stackademy LLMClients.
        :raises CommandError: If an LLMClient doesn't work.
        """
        token_record, token_key = SmarterAuthToken.objects.create(  # type: ignore[call-arg]
            user_profile=user_profile,
            name="verify_stackademy",
            user=user_profile.user,
            description="DELETE ME: single-use key created by manage.py verify_stackademy",
        )
        try:
            for name in STACKADEMY_LLMCLIENTS:
                self.verify_llmclient(name=name, user_profile=user_profile, token_key=token_key)
        finally:
            # the single-use api key is deleted, whether or not the verification succeeded.
            token_record.delete()

    def verify_llmclient(self, name: str, user_profile: UserProfile, token_key: str) -> None:
        """
        Verify that a Stackademy LLMClient answers :data:`VERIFICATION_PROMPT` with its plugin's data.

        The prompt is sent in-process to the chat api, as a client of version 2 of the chat
        contract would send it. The LLMClient works if the prompt succeeds, the LLM calls a tool,
        every tool call returns data, and the LLM answers.

        :param name: The LLMClient's name.
        :param user_profile: The owner of the LLMClient.
        :param token_key: An api key of the owner.
        :raises CommandError: If the LLMClient doesn't work.
        """
        logger.debug("%s.verify_llmclient() verifying LLMClient %s", logger_prefix, name)
        try:
            llmclient = LLMClient.objects.get(name=name, user_profile=user_profile)
        except LLMClient.DoesNotExist as e:
            raise CommandError(f"LLMClient {name} does not exist.") from e

        client = APIClient()
        headers = {"Authorization": f"Token {token_key}", "X-Smarter-Capabilities": "chat-contract-v2"}
        if smarter_settings.environment in SmarterEnvironments.aws_environments:
            headers["Host"] = smarter_settings.environment_platform_domain

        def post(path: str, body: SmarterDictType) -> SmarterDictType:
            response = client.post(f"/api/v1/llm-clients/{llmclient.id}/{path}", data=body, format="json", headers=headers)  # type: ignore[arg-type]
            if response.status_code != HTTPStatus.OK:
                raise CommandError(
                    f"LLMClient {name} {path} failed with status {response.status_code}: {response.content.decode()}"
                )
            return response.json()

        config = post("config/", {"session_key": None})
        session_key = config["data"]["session_key"]
        body = post(
            "prompt/", {"session_key": session_key, "messages": [{"role": "user", "content": VERIFICATION_PROMPT}]}
        )
        try:
            result = PromptChatApiPromptResponse.model_validate(body).data
        except ValidationError as e:
            raise CommandError(f"LLMClient {name} returned an invalid prompt response: {e}") from e

        tool_messages = [message for message in result.messages if message.role == "tool"]
        if not tool_messages:
            raise CommandError(f"LLMClient {name} did not call its plugin to answer '{VERIFICATION_PROMPT}'.")
        empty = [message.name for message in tool_messages if self.is_empty_tool_result(message)]
        if empty:
            raise CommandError(f"LLMClient {name}'s tool calls {', '.join(map(str, empty))} returned no data.")
        answers = [message for message in result.messages if message.role == "assistant" and message.content]
        if not answers:
            raise CommandError(f"LLMClient {name} did not answer '{VERIFICATION_PROMPT}'.")

        logger.debug("%s.verify_llmclient() LLMClient %s works.", logger_prefix, name)
        self.stdout.write(self.style.SUCCESS(f"LLMClient {name} works: its plugin returned course catalogue data."))

    @staticmethod
    def is_empty_tool_result(message: PromptChatApiMessage) -> bool:
        """
        True if a tool message holds no data, e.g. ``""`` or ``[]``, which a failed plugin returns.

        :param message: A message whose role is ``tool``.
        :returns: Whether the tool returned nothing.
        :rtype: bool
        """
        content = message.content
        if not isinstance(content, str):
            return not content
        try:
            return not json.loads(content)
        except json.JSONDecodeError:
            return not content.strip()
