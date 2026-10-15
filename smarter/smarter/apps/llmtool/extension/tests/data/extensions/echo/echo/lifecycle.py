"""The echo extension's lifecycle hooks, which record that they ran."""

from smarter.apps.llmtool.extension import LifecycleContext, SmarterExtensionLifecycle

CALLS: list[tuple[str, str, object]] = []
"""The hooks that ran, as (hook, version, previous version), for tests to inspect."""

FAIL: set[str] = set()
"""The hooks that tests want to fail."""


class Lifecycle(SmarterExtensionLifecycle):
    """Record every hook, and fail the ones in FAIL."""

    def record(self, hook: str, context: LifecycleContext) -> None:
        CALLS.append((hook, context.version, context.previous_version))
        if hook in FAIL:
            raise RuntimeError(f"{hook} failed")

    def pre_install(self, context):
        self.record("pre_install", context)

    def post_install(self, context):
        self.record("post_install", context)

    def pre_upgrade(self, context):
        self.record("pre_upgrade", context)

    def post_upgrade(self, context):
        self.record("post_upgrade", context)

    def pre_uninstall(self, context):
        self.record("pre_uninstall", context)

    def post_uninstall(self, context):
        self.record("post_uninstall", context)

    def on_enable(self, context):
        self.record("on_enable", context)

    def on_disable(self, context):
        self.record("on_disable", context)
