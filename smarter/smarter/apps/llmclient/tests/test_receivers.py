"""
Test :mod:`smarter.apps.llmclient.receivers`, the signal receivers of the llmclient app.

Each receiver is called directly, as a signal would call it, without and with the keyword
arguments that the signals send. The Celery tasks that some receivers queue are mocked.
"""

import inspect
from unittest.mock import MagicMock, patch

from smarter.apps.llmclient import receivers
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

TASKS = ("create_llmclient_request", "delete_default_api", "deploy_default_api", "undeploy_default_api")


def signal_kwargs() -> SmarterDictType:
    """The keyword arguments that the llmclient signals send."""
    llmclient = MagicMock(id=1, deployed=False)
    llmclient.name = "test_llmclient"
    return {
        "llmclient": llmclient,
        "llmclient_id": 1,
        "llmclient_custom_domain_id": 1,
        "account_id": 1,
        "account_number": "0000-0000-0000",
        "api_host_domain": "api.example.com",
        "certificate_arn": "arn:aws:acm:test",
        "data": {"messages": []},
        "request_data": {"messages": []},
        "domain_name": "example.com",
        "hosted_zone_id": "Z123",
        "hostname": "test.example.com",
        "name": "test_llmclient",
        "record_name": "test.example.com",
        "record_ttl": 600,
        "record_type": "A",
        "record_value": "127.0.0.1",
        "task_id": "task-1",
        "url": "https://test.example.com/",
        "with_domain_verification": True,
        "status": "deployed",
        "broker": MagicMock(),
        "plugin": MagicMock(),
        "plugin_meta": MagicMock(),
    }


class TestLLMClientReceivers(SmarterTestBase):
    """Test that each receiver handles its signal, with and without the signal's arguments."""

    def setUp(self):
        super().setUp()
        self.tasks = {}
        for name in TASKS:
            patcher = patch.object(receivers, name)
            self.tasks[name] = patcher.start()
            self.addCleanup(patcher.stop)

    def handlers(self):
        for name, function in inspect.getmembers(receivers, inspect.isfunction):
            if name.startswith("handle_") and function.__module__ == receivers.__name__:
                yield name, function

    def test_signal_handlers(self):
        handlers = list(self.handlers())
        self.assertGreater(len(handlers), 20)
        for name, handler in handlers:
            with self.subTest(handler=name):
                handler(sender=None, **signal_kwargs())
                try:
                    handler(sender=None)
                except TypeError:
                    # a receiver whose signal always sends a required argument.
                    pass

    def test_deploy_and_undeploy_queue_tasks(self):
        kwargs = signal_kwargs()
        receivers.handle_llmclient_deploy(sender=None, **kwargs)
        self.tasks["deploy_default_api"].delay.assert_called_once_with(llmclient_id=1)
        receivers.handle_llmclient_undeploy(sender=None, **kwargs)
        self.tasks["undeploy_default_api"].delay.assert_called_once_with(llmclient_id=1)

    def test_model_saved_receivers(self):
        """Test the post_save receivers of the llmclient models, for a created and an updated instance."""
        for name in (
            "llmclient_custom_domain_saved",
            "llmclient_custom_domain_dns_saved",
            "llmclient_api_key_saved",
            "llmclient_plugin_saved",
            "llmclient_extensions_saved",
            "llmclient_requests_saved",
        ):
            for created in (True, False):
                with self.subTest(receiver=name, created=created):
                    getattr(receivers, name)(sender=None, instance=MagicMock(), created=created)
        receivers.llmclient_plugin_deleted(sender=None, instance=MagicMock())

    def test_chat_requests_log_no_prompt_or_session_key(self):
        """Test that a chat request's prompt is logged at DEBUG only, and its session key only masked."""
        session_key = "77846410f51045319bd666642e325c05a7d28696407aadcfb0704827c686ad34"
        request_data = {"session_key": session_key, "messages": [{"role": "user", "content": "a private question"}]}
        with patch.object(receivers, "logger") as logger:
            receivers.handle_pre_create_llmclient_request(sender=None, llmclient_id=1, request_data=request_data)
            receivers.handle_post_create_llmclient_request(sender=None, llmclient_id=1, request_data=request_data)
            receivers.llmclient_requests_saved(sender=None, instance=MagicMock(session_key=session_key), created=True)
        logger.debug.assert_called()
        logger.info.assert_called_once()
        for call in logger.debug.call_args_list + logger.info.call_args_list:
            logged = " ".join(str(arg) for arg in call.args)
            self.assertNotIn(session_key, logged)
        self.assertIn("****86ad34", " ".join(str(arg) for arg in logger.info.call_args.args))
        self.assertNotIn("a private question", " ".join(str(arg) for arg in logger.info.call_args.args))
        # the original request data is not changed by masking it for the log.
        self.assertEqual(request_data["session_key"], session_key)
