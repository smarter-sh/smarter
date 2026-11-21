"""
Django system checks of the SAM resource apps' feature flags.

A SAM app can be turned off with its ``SMARTER_ENABLE_<APP>`` flag (see :mod:`smarter.lib.manifest.sam_apps`).
Some combinations of flags don't hold together, e.g. LLMClients enabled while Providers, which an LLMClient's
model refers to, are disabled. Rather than keep a list of dependencies by hand, these checks read them from the
models' relations:

- ``smarter.W003``: a model of an enabled SAM app has a foreign key, one-to-one or many-to-many field to a model
  of a disabled one. The enabled app's resources can't be applied or work as declared.
- ``smarter.W004``: a disabled SAM app's models still have rows. They stay in the database, unused: nothing can
  read, change or delete them through Smarter until the app is enabled again. This check reads the database, so
  it runs only with ``manage.py check --database default``.

They are registered by :class:`smarter.apps.api.apps.ApiConfig`.
"""

from typing import Any, Optional

from django.apps import apps
from django.core.checks import CheckMessage, Tags, register
from django.core.checks import Warning as CheckWarning
from django.db.models import Model

from smarter.lib.manifest.sam_apps import SAM_APPS, SamApp

DISABLED_DEPENDENCY_ID = "smarter.W003"
"""The id of the warning that an enabled SAM app's model refers to a disabled SAM app's model."""

DISABLED_APP_HAS_ROWS_ID = "smarter.W004"
"""The id of the warning that a disabled SAM app's models still have rows."""


def sam_app_of_model(model: type[Model]) -> Optional[SamApp]:
    """
    Return the SAM app that a model belongs to.

    :param model: The model class.
    :returns: The SAM app, or None for a model of a core or third-party app.
    """
    # pylint: disable=protected-access
    app_label = model._meta.app_label
    for sam_app in SAM_APPS:
        if sam_app.app_label == app_label:
            return sam_app
    return None


def disabled_dependency_warnings(settings: Any) -> list[CheckMessage]:
    """
    Warn about each relation from an enabled SAM app's model to a disabled SAM app's model.

    :param settings: The settings that hold the flags, normally ``smarter_settings``.
    :returns: One warning per relation.
    """
    warnings: list[CheckMessage] = []
    for sam_app in SAM_APPS:
        if not sam_app.is_enabled(settings):
            continue
        app_config = apps.get_app_config(sam_app.app_label)
        for model in app_config.get_models():
            # pylint: disable=protected-access
            for field in model._meta.get_fields(include_hidden=False):
                if not field.is_relation or field.auto_created:
                    continue
                related_model = field.related_model
                if not isinstance(related_model, type):
                    continue
                related_app = sam_app_of_model(related_model)
                if related_app is None or related_app.is_enabled(settings):
                    continue
                warning = CheckWarning(
                    f"{model.__name__}.{field.name} refers to {related_model.__name__}, of the {related_app.label} "
                    f"app, which is disabled, while the {sam_app.label} app is enabled.",
                    hint=f"Set {related_app.env_name}=true, or {sam_app.env_name}=false.",
                    obj=model,
                    id=DISABLED_DEPENDENCY_ID,
                )
                warnings.append(warning)
    return warnings


def disabled_app_rows_warnings(settings: Any) -> list[CheckMessage]:
    """
    Warn about each disabled SAM app whose models still have rows.

    :param settings: The settings that hold the flags, normally ``smarter_settings``.
    :returns: One warning per disabled app that has rows.
    """
    warnings: list[CheckMessage] = []
    for sam_app in SAM_APPS:
        if sam_app.is_enabled(settings):
            continue
        app_config = apps.get_app_config(sam_app.app_label)
        models_with_rows = []
        for model in app_config.get_models():
            # pylint: disable=protected-access
            if model._meta.proxy or not model._meta.managed:
                continue
            if model._default_manager.exists():
                models_with_rows.append(model.__name__)
        if not models_with_rows:
            continue
        warning = CheckWarning(
            f"The {sam_app.label} app is disabled, but its models still have rows: {', '.join(models_with_rows)}.",
            hint=(
                f"They can't be read, changed or deleted through Smarter until {sam_app.env_name}=true. "
                "Delete them first if they aren't needed."
            ),
            id=DISABLED_APP_HAS_ROWS_ID,
        )
        warnings.append(warning)
    return warnings


@register()
def check_sam_app_dependencies(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """
    Warn about enabled SAM apps whose models refer to a disabled SAM app's models.

    :param app_configs: The apps to check, or None for all of them. Ignored: the check is about the whole platform.
    :returns: The warnings.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.common.conf import smarter_settings

    return disabled_dependency_warnings(smarter_settings)


@register(Tags.database)
def check_disabled_sam_app_rows(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    """
    Warn about disabled SAM apps whose models still have rows.

    Runs only with ``manage.py check --database``.

    :param app_configs: The apps to check, or None for all of them. Ignored: the check is about the whole platform.
    :param kwargs: Django's, among them ``databases``, which ``--database`` names. The check does nothing without one.
    :returns: The warnings.
    """
    databases = kwargs.get("databases")
    if not databases:
        return []
    # pylint: disable=import-outside-toplevel
    from smarter.common.conf import smarter_settings

    return disabled_app_rows_warnings(smarter_settings)


__all__ = [
    "DISABLED_APP_HAS_ROWS_ID",
    "DISABLED_DEPENDENCY_ID",
    "check_disabled_sam_app_rows",
    "check_sam_app_dependencies",
    "disabled_app_rows_warnings",
    "disabled_dependency_warnings",
    "sam_app_of_model",
]
