"""
Test that an LLMClient's Vectorsearches are offered to the LLM as search tools, and answer its calls.

This tests :meth:`OpenAISmarterClient.handle_vectorsearches` and the Vectorsearch branch of
:meth:`OpenAISmarterClient.process_tool_call`, with a mocked LLM that searches a Vectorsearch, whose
vectorstore is in-memory Qdrant with fake embeddings.
"""

import secrets
from unittest import mock

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from pydantic import SecretStr

from smarter.apps.llmclient.models import LLMClient, LLMClientVectorsearches
from smarter.apps.prompt.models import Prompt
from smarter.apps.provider.models import Provider
from smarter.apps.provider.services.text_completion.const import OpenAIMessageKeys
from smarter.apps.provider.services.text_completion.lib.internal_keys import (
    _InternalKeys,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    OpenAISmarterClient,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.toolkit import function_name_for
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase

from .test_extension_prompt_integration import (
    CREATE_PATCH,
    PROMPT_TASK_PATCHES,
    SYSTEM_ROLE,
    completion,
)

SERVICE_PATCH = "smarter.apps.vectorsearch.toolkit.VectorstoreService"


class TestVectorsearchPromptIntegration(VectorstoreTestBase):
    """Test an LLMClient's Vectorsearches in a prompt."""

    def setUp(self):
        super().setUp()
        for target in PROMPT_TASK_PATCHES:
            patcher = mock.patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.vectorstore_service = self.ready_service("test_vectorsearch_prompt")
        document, _ = self.vectorstore_service.add_document(
            name="handbook.txt", text="Refunds are available within 30 days of enrollment. " * 20
        )
        self.vectorstore_service.load_document(document)
        self.vectorsearch = Vectorsearch.objects.create(
            name=f"handbook_{self.hash_suffix}",
            description="Searches the student handbook.",
            user_profile=self.user_profile,
            vectorstore=self.vectorstore_service.vectorstore,
            k=2,
        )
        self.addCleanup(Vectorsearch.objects.filter(pk=self.vectorsearch.pk).delete)
        self.llmclient = LLMClient.objects.create(
            name=f"test_vectorsearch_prompt_{self.hash_suffix}",
            user_profile=self.user_profile,
            deployed=False,
            app_name="Smarter",
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=self.user_profile,
            llmclient=self.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.test.com",
        )
        self.addCleanup(Prompt.objects.filter(pk=self.prompt.pk).delete)
        # the toolkit makes a service for the vectorstore: the test's in-memory one.
        service_patcher = mock.patch(SERVICE_PATCH, lambda vectorstore: self.vectorstore_service)
        service_patcher.start()
        self.addCleanup(service_patcher.stop)

    def chat_provider(self) -> OpenAISmarterClient:
        """Return a chat provider for the test prompt."""
        provider_orm = Provider.objects.filter(name="openai").first()
        if provider_orm is None:
            self.skipTest("the platform's openai Provider does not exist.")
        return OpenAISmarterClient(
            provider=provider_orm,
            provider_name="openai",
            base_url="https://api.example.com/v1/",
            api_key=SecretStr("sk-test"),
            default_model="gpt-6-luna",
        )

    def data(self, text: str) -> dict:
        """Return the request body of a prompt."""
        return {
            "session_key": self.prompt.session_key,
            "messages": [{"role": "system", "content": SYSTEM_ROLE}, {"role": "user", "content": text}],
        }

    def test_search_tool_call(self):
        """The LLM is offered the Vectorsearch as a tool, and its search is answered with the documents' passages."""
        LLMClientVectorsearches.objects.create(llmclient=self.llmclient, vectorsearch=self.vectorsearch)
        function_name = function_name_for(self.vectorsearch)
        tool_call = ChatCompletionMessageToolCall(
            id="call_1", type="function", function=Function(name=function_name, arguments='{"query": "refunds"}')
        )
        provider = self.chat_provider()
        with mock.patch(
            CREATE_PATCH, side_effect=[completion(tool_calls=[tool_call]), completion("Within 30 days.")]
        ) as create:
            provider.handler(self.user_profile, self.prompt, self.data("Can I get a refund?"))
        offered = create.call_args_list[0].kwargs["tools"]
        tool = next(tool for tool in offered if tool["function"]["name"] == function_name)
        self.assertEqual(tool["function"]["description"], "Searches the student handbook.")

        second_request = create.call_args_list[1].kwargs["messages"]
        tool_messages = [m for m in second_request if m.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == "tool"]
        self.assertIn("Refunds are available within 30 days", tool_messages[0][OpenAIMessageKeys.MESSAGE_CONTENT_KEY])

        serialized = provider.serialized_tool_calls[0]  # type: ignore[index]
        self.assertEqual(
            serialized[_InternalKeys.SMARTER_VECTORSEARCH_KEY],
            {
                "id": self.vectorsearch.pk,
                "name": self.vectorsearch.name,
                "vectorstore": self.vectorstore_service.vectorstore.name,
            },
        )
        self.assertEqual(provider.tool_display_name(function_name), self.vectorsearch.name)
        # the documents may change, so an answer that searched them is not cached.
        self.assertFalse(provider.prompt_cacheable)
        provider_messages = provider.messages
        assert provider_messages is not None
        smarter_messages = [
            m.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY) for m in provider_messages if m.get("role") == "smarter"
        ]
        self.assertTrue(
            any(f"search tool for these vectorsearches: {self.vectorsearch.name}" in str(m) for m in smarter_messages)
        )

    def test_no_vectorsearches(self):
        """An LLMClient without Vectorsearches has no Vectorsearch toolkit, and offers no search tool."""
        provider = self.chat_provider()
        provider.prompt = self.prompt
        provider.handle_vectorsearches()
        self.assertIsNone(provider.vectorsearch_toolkit)
        self.assertIsNone(provider.call_vectorsearch_tool("smarter_vectorsearch_0", {}, {}, []))
        provider._chat = None  # pylint: disable=protected-access
        provider.handle_vectorsearches()
        self.assertIsNone(provider.vectorsearch_toolkit)
