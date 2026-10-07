"""
Shared tests for the not-found, not-ready and failure branches of a SAM broker.

These brokers share one layout: a resource property named for the kind (``orchestrator``,
``vectorsearch``, ...), describe() and delete() that look the resource up by name,
deploy() and undeploy() that aren't implemented, and an apply() guarded by
ready, manifest and resource checks.
"""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.broker import SAMBrokerError, SAMBrokerErrorNotReady
from smarter.lib.manifest.loader import SAMLoader


class BrokerBranchesTestMixin:
    """
    Mix into a TestAccountMixin subclass, and set the class attributes below.

    :cvar broker_class: The broker class under test.
    :cvar error_class: The broker's own SAMBrokerError subclass.
    :cvar resource_property: The name of the broker property that returns the resource.
    :cvar model: The resource's Django model.
    :cvar manifest_path: Path to a manifest of the broker's kind.
    """

    broker_class: type
    error_class: type
    resource_property: str
    model: type
    manifest_path: str

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.request = self.create_generic_request("/anywhere/")  # type: ignore[attr-defined]
        self.request.user = self.admin_user  # type: ignore[attr-defined]
        self.loader = SAMLoader(manifest=get_readonly_yaml_file(self.manifest_path))
        self.broker = self.broker_class(request=self.request, account=self.account, loader=self.loader)  # type: ignore[attr-defined]

    def patch_property(self, name: str, value) -> PropertyMock:
        patcher = patch.object(self.broker_class, name, new_callable=PropertyMock, return_value=value)
        mock = patcher.start()
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        return mock

    def patch_method(self, name: str, **kwargs) -> MagicMock:
        patcher = patch.object(self.broker, name, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        return mock

    def test_describe_and_delete_need_a_name(self):
        """Describe and delete aren't ready without a name."""
        self.patch_property("name", None)
        for command in ("describe", "delete"):
            with self.subTest(command=command), self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                getattr(self.broker, command)(self.request)

    def test_describe_and_delete_need_the_resource(self):
        """Describe and delete aren't ready when the resource doesn't exist."""
        self.patch_property("name", "no_such_resource")
        self.patch_property(self.resource_property, None)
        self.patch_method("verify_no_dependencies")
        for command in ("describe", "delete"):
            with self.subTest(command=command), self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                getattr(self.broker, command)(self.request)

    def test_describe_and_delete_failures(self):
        """A failure in describe or delete is reported as the broker's error."""
        resource = MagicMock(spec=self.model)
        resource.delete.side_effect = RuntimeError("delete failed")
        self.patch_property("name", "failing_resource")
        self.patch_property(self.resource_property, resource)
        self.patch_method("verify_no_dependencies")
        self.patch_method("cache_invalidations")
        self.patch_method("django_orm_to_manifest_dict", side_effect=RuntimeError("dump failed"))
        for command in ("describe", "delete"):
            with self.subTest(command=command), self.assertRaises(self.error_class):  # type: ignore[attr-defined]
                getattr(self.broker, command)(self.request)

    def test_deploy_undeploy_logs_and_dependencies(self):
        """Deploy and undeploy aren't implemented, logs is empty, and nothing depends on the resource."""
        for command in ("deploy", "undeploy"):
            with self.subTest(command=command), self.assertRaises(SAMBrokerError):  # type: ignore[attr-defined]
                getattr(self.broker, command)(self.request)
        self.assertEqual(self.broker.logs(self.request).status_code, 200)  # type: ignore[attr-defined]
        self.assertEqual(self.broker.dependencies(), [])  # type: ignore[attr-defined]

    def test_conversions_need_a_manifest_account_and_user_profile(self):
        """The ORM conversions need a manifest, an account, a user profile and the resource."""
        with patch.object(self.broker_class, "manifest", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                self.broker.manifest_to_django_orm()
        for name in ("account", "user_profile"):
            with patch.object(self.broker_class, name, new_callable=PropertyMock, return_value=None):
                with self.subTest(missing=name), self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                    self.broker.django_orm_to_manifest_dict()
        self.patch_property(self.resource_property, None)
        self.assertIsNone(self.broker.django_orm_to_manifest_dict())  # type: ignore[attr-defined]

    def test_manifest_of_the_wrong_type(self):
        """A cached manifest of the wrong type is rejected."""
        self.broker._manifest = {"kind": "Wrong"}
        with self.assertRaises(self.error_class):  # type: ignore[attr-defined]
            _ = self.broker.manifest

    def test_apply_guards(self):
        """Apply needs a ready broker, a manifest with a spec, and the resource."""
        with patch.object(self.broker_class, "ready", new_callable=PropertyMock, return_value=False):
            with self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                self.broker.apply(self.request)
        self.patch_property("ready", True)
        with patch.object(self.broker_class, "manifest", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                self.broker.apply(self.request)
        without_spec = MagicMock()
        without_spec.spec = None
        with patch.object(self.broker_class, "manifest", new_callable=PropertyMock, return_value=without_spec):
            with self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
                self.broker.apply(self.request)
        self.patch_property(self.resource_property, None)
        with self.assertRaises(self.error_class):  # type: ignore[attr-defined]
            self.broker.apply(self.request)

    def test_apply_failure(self):
        """A failure while saving is reported as the broker's error."""
        self.patch_property("ready", True)
        self.patch_property(self.resource_property, MagicMock(spec=self.model))
        self.patch_method("manifest_to_django_orm", side_effect=RuntimeError("conversion failed"))
        with self.assertRaises(self.error_class):  # type: ignore[attr-defined]
            self.broker.apply(self.request)

    def test_get_needs_a_user_profile(self):
        """Get isn't ready without a user profile."""
        self.patch_property("user_profile", None)
        with self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
            self.broker.get(self.request)


def api_test_data(app: str, filename: str) -> str:
    """Return the path of a manifest in an app's ``api/v1/views/tests/data`` folder."""
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(here, "apps", app, "api", "v1", "views", "tests", "data", filename)
