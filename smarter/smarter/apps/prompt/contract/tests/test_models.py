"""Test :mod:`smarter.apps.prompt.contract.models` against the shapes that Smarter Chat reads."""

from datetime import datetime, timezone
from typing import get_args
from unittest.mock import MagicMock

from pydantic import ValidationError

from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.prompt.contract.models import (
    PromptChatApiCompletion,
    PromptChatApiCompletionV1,
    PromptChatApiConfig,
    PromptChatApiConfigResponse,
    PromptChatApiConfigResponseV1,
    PromptChatApiErrorResponse,
    PromptChatApiFailureV1,
    PromptChatApiHistory,
    PromptChatApiLLMClientExtension,
    PromptChatApiLLMClientPlugin,
    PromptChatApiLLMClientRequest,
    PromptChatApiMessage,
    PromptChatApiPluginClass,
    PromptChatApiPluginMeta,
    PromptChatApiPluginSelection,
    PromptChatApiProgressEvent,
    PromptChatApiProgressEventType,
    PromptChatApiProgressResult,
    PromptChatApiPromptPluginUsage,
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
    PromptChatApiPromptResponseV1,
    PromptChatApiPromptToolCall,
    legacy_key_names,
)
from smarter.apps.prompt.progress import PromptProgressEvents
from smarter.lib.unittest.base_classes import SmarterTestBase

SESSION_KEY = "e019a5c1cb2c1cb87992d2d03bccaf44c9d98406b46de5516a4fa03650038ac8"
ENVELOPE = {"api": "smarter.sh/v1", "metadata": {"command": "prompt_config", "thing": "PromptConfig"}}
LLMCLIENT = {"id": 1, "name": "stackademy", "app_name": "Stackademy"}
COMMON = {
    "session_key": SESSION_KEY,
    "sandbox_mode": True,
    "debug_mode": False,
    "meta_data": {"ready": True},
    "plugins": {"meta_data": {"total_plugins": 0, "plugins_returned": 0}, "plugins": []},
}


class TestChatContractModels(SmarterTestBase):
    """Test the Pydantic models of the Smarter Chat api contract."""

    def test_config_v2(self):
        response = PromptChatApiConfigResponse.model_validate(
            {
                **ENVELOPE,
                "data": {
                    **COMMON,
                    "contract": 2,
                    "llmclient": {**LLMCLIENT, "url_llmclient": "https://x/prompt/", "anything": "else"},
                    "history": {"chat_history": [{"role": "system", "content": "hi"}]},
                },
            }
        )
        self.assertEqual(response.data.llmclient.url_llmclient, "https://x/prompt/")
        # extra fields are allowed, and kept.
        self.assertEqual(response.model_dump()["data"]["llmclient"]["anything"], "else")

    def test_config_v1(self):
        response = PromptChatApiConfigResponseV1.model_validate(
            {
                **ENVELOPE,
                "data": {
                    **COMMON,
                    "chatbot": {**LLMCLIENT, "url_chatbot": "https://x/prompt/"},
                    "history": {"chat_history": [], "chatbot_request_history": []},
                },
            }
        )
        self.assertEqual(response.data.chatbot.url_chatbot, "https://x/prompt/")

    def test_config_v1_requires_the_legacy_url(self):
        with self.assertRaises(ValidationError):
            PromptChatApiConfigResponseV1.model_validate(
                {**ENVELOPE, "data": {**COMMON, "chatbot": LLMCLIENT, "history": {}}}
            )

    def test_prompt_shapes(self):
        PromptChatApiPromptRequest.model_validate(
            {"session_key": SESSION_KEY, "messages": [{"role": "assistant", "content": None, "tool_calls": []}]}
        )
        PromptChatApiPromptResponseV1.model_validate({**ENVELOPE, "data": {"statusCode": 200, "body": "{}"}})
        PromptChatApiCompletionV1.model_validate(
            {"id": "x", "smarter": {"messages": [{"role": "smarter", "content": "s"}]}}
        )
        PromptChatApiFailureV1.model_validate(
            {"error": {"status": 401, "message": "no"}, "response": {"smarter": {"messages": []}}}
        )
        PromptChatApiErrorResponse.model_validate({"error": {"errorClass": "X", "description": "no", "status": 404}})

    def test_progress_events(self):
        PromptChatApiProgressEvent.model_validate({"type": "tool_requested", "message": "Calling tool x", "tool": "x"})
        response = {
            **ENVELOPE,
            "data": {"contract": 2, "status": 200, "messages": [{"role": "assistant", "content": "hi"}]},
        }
        result = PromptChatApiProgressResult.model_validate({"status": 200, "response": response})
        self.assertIsInstance(result.response, PromptChatApiPromptResponse)
        with self.assertRaises(ValidationError):
            PromptChatApiProgressEvent.model_validate({"type": "unknown", "message": "x"})

    def test_progress_event_types_match_the_progress_module(self):
        """A new progress event type must be added to the contract too."""
        emitted = {value for name, value in vars(PromptProgressEvents).items() if name.isupper()}
        self.assertEqual(set(get_args(PromptChatApiProgressEventType)), emitted)


PLUGIN_META = {"id": 16, "name": "stackademy_sql", "plugin_class": "sql", "tags": ["db"], "version": "0.1.0"}


def complete_config() -> PromptChatApiConfig:
    """A complete configuration, as PromptConfigView.chat_config() builds it."""
    return PromptChatApiConfig(
        contract=2,
        session_key=SESSION_KEY,
        sandbox_mode=False,
        debug_mode=False,
        llmclient={
            **LLMCLIENT,
            "url_llmclient": "https://stackademy.3141-5926-5359.api.example.com/prompt/",
            "user_profile": {"user": {"username": "owner", "email": "owner@example.com"}, "account_number": "1"},
            "default_temperature": 0.5,
            "total_tools": 3,
        },
        history={
            "chat_history": [{"role": "user", "content": "hi"}],
            "llmclient_request_history": [
                {
                    "id": 1,
                    "llmclient": 1,
                    "request": {"session_key": SESSION_KEY, "messages": [{"role": "system", "content": "secret"}]},
                }
            ],
            "prompt_tool_call_history": [{"id": 1, "prompt": 1, "function_name": "calculator", "response": {"x": [1]}}],
        },
        meta_data={"ready": True, "is_deployed": True, "account": {"account_number": "1"}, "url": "x"},
        plugins={
            "meta_data": {"total_plugins": 2, "plugins_returned": 2},
            "plugins": [
                {"id": 1, "llmclient": 1, "plugin_meta": PLUGIN_META},
                {"id": 2, "llmclient": 1, "plugin_meta": PLUGIN_META},
            ],
        },
        extensions={
            "meta_data": {"total_extensions": 1, "extensions_returned": 1},
            "extensions": [
                {"id": 1, "llmclient": 1, "extension": 3, "name": "weather", "version": "1.0.0", "enabled": True}
            ],
        },
    )


class TestChatConfigTransformations(SmarterTestBase):
    """Test PromptChatApiConfig.public() and PromptChatApiConfig.to_v1(), from which the configuration api's responses are derived."""

    def test_public(self):
        data = complete_config().public().model_dump(mode="json", exclude_unset=True)
        self.assertEqual(data["contract"], 2)
        self.assertNotIn("user_profile", data["llmclient"])
        self.assertNotIn("default_temperature", data["llmclient"])
        self.assertEqual(data["llmclient"]["total_tools"], 3)
        self.assertEqual(data["llmclient"]["url_llmclient"], complete_config().llmclient.url_llmclient)
        self.assertEqual(data["history"], {"chat_history": [{"role": "user", "content": "hi"}]})
        self.assertEqual(data["meta_data"], {"ready": True, "is_deployed": True})
        self.assertEqual(data["plugins"], {"meta_data": {"total_plugins": 2, "plugins_returned": 2}, "plugins": []})
        self.assertEqual(data["extensions"]["extensions"], [])
        self.assertNotIn("owner@example.com", str(data))
        PromptChatApiConfigResponse.model_validate({**ENVELOPE, "data": data})

    def test_public_without_extensions(self):
        config = complete_config()
        config.extensions = None
        self.assertIsNone(config.public().extensions)

    def test_complete_v2_keeps_every_field(self):
        data = complete_config().model_dump(mode="json", exclude_unset=True)
        self.assertEqual(data["llmclient"]["user_profile"]["user"]["username"], "owner")
        self.assertEqual(len(data["plugins"]["plugins"]), 2)

    def test_to_v1(self):
        v1 = complete_config().to_v1()
        data = v1.model_dump(mode="json", exclude_unset=True)
        self.assertNotIn("contract", data)
        self.assertEqual(data["chatbot"]["url_chatbot"], complete_config().llmclient.url_llmclient)
        self.assertEqual(data["chatbot"]["user_profile"]["accountNumber"], "1")
        self.assertIn("chatbot_request_history", data["history"])
        self.assertNotIn("llmclient", str(list(data)))
        self.assertEqual(data["extensions"]["extensions"][0]["chatbot"], 1)
        PromptChatApiConfigResponseV1.model_validate({**ENVELOPE, "data": data})

    def test_legacy_key_names_renames_keys_at_every_depth(self):
        renamed = legacy_key_names(
            {
                "llmclient": {"url_llmclient": "u", "user_profile": [{"account_number": "1"}]},
                "history": {"prompt_history": [], "llmclient_request_history": []},
                "values": ["llmclient stays a value"],
            }
        )
        self.assertEqual(renamed["chatbot"]["url_chatbot"], "u")
        self.assertEqual(renamed["chatbot"]["user_profile"], [{"accountNumber": "1"}])
        self.assertEqual(set(renamed["history"]), {"chat_history", "chatbot_request_history"})
        self.assertEqual(renamed["values"], ["llmclient stays a value"])

    def test_a_configuration_that_breaks_the_contract(self):
        for overrides in ({"session_key": "not a session key"}, {"llmclient": {"id": 1, "name": "x"}}):
            with self.subTest(overrides=list(overrides)):
                with self.assertRaises(ValidationError):
                    PromptChatApiConfig(**{**complete_config().model_dump(), **overrides})


class TestOrmModels(SmarterTestBase):
    """Test the contract's models of the LLMClient's plugins and extensions, which mirror their Django ORM rows."""

    def test_plugin_classes_match_the_orm(self):
        self.assertEqual(set(get_args(PromptChatApiPluginClass)), {value for value, _ in PluginMeta.PLUGIN_CLASSES})

    def test_from_model(self):
        now = datetime.now(timezone.utc)
        tags = MagicMock()
        tags.all.return_value = [MagicMock(), MagicMock()]
        tags.all.return_value[0].name = "db"
        tags.all.return_value[1].name = "sql"
        plugin_meta = MagicMock(
            pk=16,
            created_at=now,
            updated_at=now,
            description="Query the catalogue.",
            version="0.1.0",
            tags=tags,
            annotations={},
            plugin_class="sql",
        )
        plugin_meta.name = "stackademy_sql"
        plugin = MagicMock(pk=1, created_at=now, updated_at=now, llmclient_id=7, plugin_meta=plugin_meta)
        model = PromptChatApiLLMClientPlugin.from_model(plugin)
        self.assertEqual(model.llmclient, 7)
        self.assertEqual(model.plugin_meta.name, "stackademy_sql")
        self.assertEqual(model.plugin_meta.tags, ["db", "sql"])
        self.assertEqual(model.plugin_meta.plugin_class, "sql")

        extension = MagicMock(pk=3, slug="weather", enabled=True, installed_version=MagicMock(version="1.0.0"))
        link = MagicMock(pk=2, created_at=now, updated_at=now, llmclient_id=7, extension=extension)
        model = PromptChatApiLLMClientExtension.from_model(link)
        self.assertEqual((model.name, model.extension, model.version, model.enabled), ("weather", 3, "1.0.0", True))
        extension.installed_version = None
        self.assertIsNone(PromptChatApiLLMClientExtension.from_model(link).version)

    def test_orm_models_are_strict(self):
        """The models of ORM rows have exactly their fields: an extra field, or an unknown choice, is an error."""
        with self.assertRaises(ValidationError):
            PromptChatApiLLMClientPlugin(id=1, llmclient=1, plugin_meta=PLUGIN_META, user_profile={"email": "x"})
        with self.assertRaises(ValidationError):
            PromptChatApiPluginMeta(**{**PLUGIN_META, "plugin_class": "PluginMeta"})
        with self.assertRaises(ValidationError):
            PromptChatApiLLMClientExtension(id=1, llmclient=1, extension=1, name="weather", enabled=True, secret="x")

    def test_v1_models_are_deprecated(self):
        with self.assertWarns(DeprecationWarning):
            complete_config().to_v1()


class TestStrictTypes(SmarterTestBase):
    """Test the types that replace untyped lists: message parts, tool calls, history rows and JSON values."""

    def test_message_parts_and_tool_calls(self):
        message = PromptChatApiMessage.model_validate(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/a.png", "detail": "low"}},
                ],
            }
        )
        self.assertEqual(message.content[1].image_url.url, "https://example.com/a.png")  # type: ignore[index,union-attr]
        with self.assertRaises(ValidationError):
            PromptChatApiMessage.model_validate({"role": "user", "content": [{"type": "video", "video": "x"}]})
        assistant = PromptChatApiMessage.model_validate(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "f", "arguments": "{}"}}],
            }
        )
        self.assertEqual(assistant.tool_calls[0].function.name, "f")  # type: ignore[index]

    def test_history_has_exactly_its_fields(self):
        with self.assertRaises(ValidationError):
            PromptChatApiHistory(chat_history=[], prompt={"id": 1})  # type: ignore[call-arg]

    def test_history_rows_from_their_models(self):
        now = datetime.now(timezone.utc)
        tool_call = MagicMock(
            pk=1,
            created_at=now,
            updated_at=now,
            prompt_id=2,
            plugin_id=None,
            function_name="calculator",
            function_args="{}",
            request={"expression": "1+1"},
            response=[{"result": 2}],
        )
        self.assertEqual(PromptChatApiPromptToolCall.from_model(tool_call).response, [{"result": 2}])
        usage = MagicMock(pk=1, created_at=now, updated_at=now, prompt_id=2, plugin_id=16, input_text="hi")
        self.assertEqual(PromptChatApiPromptPluginUsage.from_model(usage).plugin, 16)
        selection = MagicMock(
            pk=1,
            created_at=now,
            updated_at=now,
            plugin_selector_id=3,
            search_term="ai",
            messages=[{"role": "user", "content": "ai?"}],
            session_key=SESSION_KEY,
        )
        self.assertEqual(PromptChatApiPluginSelection.from_model(selection).messages[0].content, "ai?")  # type: ignore[index]
        request = MagicMock(
            pk=1,
            created_at=now,
            updated_at=now,
            llmclient_id=4,
            session_key=SESSION_KEY,
            is_aggregation=False,
            request={"session_key": SESSION_KEY, "messages": [{"role": "user", "content": "hi"}]},
        )
        self.assertEqual(PromptChatApiLLMClientRequest.from_model(request).request.messages[0].content, "hi")  # type: ignore[union-attr]

    def test_completion_keeps_only_its_fields(self):
        completion = PromptChatApiCompletion.model_validate(
            {
                "id": "x",
                "choices": [{"index": 0, "finish_reason": "length", "message": {"role": "assistant", "content": ""}}],
                "usage": {"completion_tokens": 9, "completion_tokens_details": {"reasoning_tokens": 9}},
                "metadata": {"tool_calls": [{"smarter_plugin": {"user_profile": {"email": "owner@example.com"}}}]},
            }
        )
        dumped = completion.model_dump(mode="json")
        self.assertNotIn("metadata", dumped)
        self.assertEqual(dumped["usage"]["completion_tokens_details"]["reasoning_tokens"], 9)
