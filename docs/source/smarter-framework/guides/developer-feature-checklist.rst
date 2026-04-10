New Feature Checklist
========================

This checklist is intended to help you, a Smarter developer contributor, ensure that
any new feature you’re working on is fully integrated into the Smarter framework
and is ready for production deployment. Smarter provides a wide range of base classes,
helper mixins, and subsystems that you must utilize to ensure your feature's
compatibility and maintainability within the Smarter ecosystem. Plus, following
these rules will save you time and improve the quality of your code.

1. Run pre-commit hooks prior to pushing your code
2. Use Smarter's base and helper classes and subsystems where relevant, especially the following:
    - :class:`smarter.apps.account.mixins.AccountMixin`
    - :class:`smarter.lib.django.request.SmarterRequestMixin`
    - :class:`smarter.common.mixins.SmarterHelperMixin`
    - :class:`smarter.lib.django.validators.SmarterValidator`
    - :class:`smarter.apps.account.tests.mixins.TestAccountMixin`
    - :class:`smarter.lib.drf.serializers.SmarterCamelCaseSerializer` and :class:`smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer`
    - :class:`smarter.lib.manifest.broker.AbstractBroker`
    - :class:`smarter.lib.manifest.models.AbstractSAMBase`
    - get_cached_object() and get_cached_objects() class methods on SAM ORM models
    - :func:`smarter.lib.cache.cache_results` decorator
3. Add your documentation to docs/source and test with make sphinx-docs
4. Ensure that your logging entries conform to the `Smarter logging style guidelines <../smarter-logging.html>`__
5. Ensure that your unit test coverage ratio is at least 85% for any new code you add.
6. Register the Django app in the `INSTALLED_APPS` list in `settings.py`.
7. Add your app's top-level urls.py to smarter/urls/.
8. Ensure that your Django models inherit from smarter.lib.django.models.
9.  Include database migrations for any new models.
10. Include serializers for all models
11. Add API views and viewsets, and ensure they cover all models
12. Add Django admin classes for all models using smarter.apps.dashboard.admin.SmarterCustomerModelAdmin
13. Add your new settings to smarter.common.conf.SmarterSettings and include sensible defaults and documentation for each setting.
14. Include a tasks module
15. Include a management commands module
16. Include signals and receivers modules.
17. Include SAM models and brokers for each relevant ORM model.
18. Ensure that all classes and functions have Sphinx-compatible docstrings.
19. Ensure that your code adheres to PEP 8 style guidelines.
20. Add new Smarter resource kinds to :class:`smarter.apps.api.v1.manifests.enum.SAMKinds`
21. Add waffle logging and feature switches as necessary to :class:`smarter.lib.django.waffle.SmarterWaffleSwitches`
22. Ensure that your UI includes anchors as necessary in :file:`smarter/templates/dashboard/authenticated.html`
23. Ensure that exceptions are properly handled and that you have inherited from :class:`smarter.common.exceptions.SmarterException`
