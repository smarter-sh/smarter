# Canonical Test References

Read these before writing a new test module. Copy their structure.

| Kind of test                                                        | Reference                                                                            | Why it's the reference                                                                                                                                                                   |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SAM broker                                                          | `smarter/smarter/apps/llmclient/manifest/brokers/tests/test_custom_domain_broker.py` | Subclasses `TestSAMBrokerBaseClass`. Loads the manifest from `data/`, cleans up with `addCleanup` and `tearDownClass`, and covers apply, describe, get, delete, dependencies, and errors |
| Resource views (list page, list api, clone, rename, delete, detail) | `smarter/smarter/apps/llmclient/tests/test_custom_domain_views.py`                   | `ResourceViewsTestMixin` plus a `ReverseNames` adapter, with only the resource-specific tests written out                                                                                |
| Guardrail app, many modules                                         | `smarter/smarter/apps/guardrail/tests/`                                              | One module per source module, plus `base_classes.py` and `data/`                                                                                                                         |
| Plugins, shared fixtures                                            | `smarter/smarter/apps/plugin/plugin/tests/`                                          | `base_classes.py` with mixins, and `mock_remote_skills()`                                                                                                                                |
| Celery task, mocked infrastructure                                  | `smarter/smarter/apps/llmclient/tests/tasks/test_task_verify_custom_domain.py`       | Calls the task function directly. `infrastructure` is a `MagicMock` patched into the task module, and `apply_async` is patched so that retries don't reach the worker                    |
| Management command                                                  | `smarter/smarter/apps/llmclient/tests/test_add_builtin_custom_domains.py`            | `call_command` with captured stdout. The Celery task the command queues is patched in the command module, so nothing reaches the worker                                                  |

## Skeleton: SAM broker test

```python
"""Test SAMWidgetBroker."""

from smarter.apps.widget.manifest.brokers.widget import SAMWidgetBroker
from smarter.apps.widget.models import Widget
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass


class TestSmarterWidgetBroker(TestSAMBrokerBaseClass):
    """Test the Smarter SAMWidgetBroker."""

    @classmethod
    def tearDownClass(cls):
        Widget.objects.filter(user_profile__account=cls.account).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._manifest_filespec = self.get_data_full_filepath("widget.yaml")
        self.addCleanup(Widget.objects.filter(user_profile=self.user_profile).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMWidgetBroker]:
        return SAMWidgetBroker

    def test_apply(self):
        """Apply() creates the Widget, owned by the user."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertTrue(Widget.objects.filter(user_profile=self.user_profile, name="test_widget").exists())
```

## Skeleton: resource views test

```python
class TestWidgetViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Widget dashboard views."""

    model = Widget
    reverse_names = WidgetReverseNames
    id_kwarg = "widget_id"
    resource_name_prefix = "test_widget_views"

    @classmethod
    def create_resource(cls, name: str) -> Widget:
        return Widget.objects.create(name=name, user_profile=cls.user_profile)
```

## Mocking pattern

Patch the name **where the code under test looks it up**: the task's own
module, not the module that defines the helper. Start patchers in `setUp` and
stop them with `addCleanup`:

```python
from unittest.mock import MagicMock, patch

from smarter.apps.llmclient.tasks.verify_custom_domain import verify_custom_domain

MODULE = "smarter.apps.llmclient.tasks.verify_custom_domain"


def setUp(self):
    super().setUp()
    infrastructure = MagicMock()
    infrastructure.certificates.certificate_status.return_value = "ISSUED"
    for target, value in (("infrastructure", infrastructure), ("is_taskable", MagicMock(return_value=True))):
        patcher = patch(f"{MODULE}.{target}", value)
        patcher.start()
        self.addCleanup(patcher.stop)
    patcher = patch.object(verify_custom_domain, "apply_async")   # no re-queued retries
    self.apply_async = patcher.start()
    self.addCleanup(patcher.stop)

def test_verified(self):
    self.assertTrue(verify_custom_domain(self.hosted_zone_id))   # called directly, not .delay()
    ...
```
