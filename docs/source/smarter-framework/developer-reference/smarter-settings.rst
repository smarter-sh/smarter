Smarter Settings
================

.. automodule:: smarter.common.conf
   :no-members:
   :no-inherited-members:
   :no-special-members:

``smarter_settings`` is one instance of :class:`~smarter.common.conf.settings.Settings`, which
combines a Pydantic model per topic. Each topic's module, in the package
:mod:`smarter.common.conf.settings`, holds its fields, their validators, and the properties
derived from them. A new setting goes into the topic it belongs to.

.. autopydantic_model:: smarter.common.conf.Settings

Topics
------

.. autopydantic_model:: smarter.common.conf.settings.platform.PlatformSettings

.. autoclass:: smarter.common.const.SmarterKubernetesPodKinds
   :members:
   :no-index:

.. autoclass:: smarter.common.const.SmarterPodCapabilities
   :members:
   :no-index:

.. autopydantic_model:: smarter.common.conf.settings.domains.DomainSettings

.. autopydantic_model:: smarter.common.conf.settings.aws.AwsSettings

.. autopydantic_model:: smarter.common.conf.settings.branding.BrandingSettings

.. autopydantic_model:: smarter.common.conf.settings.cache.CacheSettings

.. autopydantic_model:: smarter.common.conf.settings.database.DatabaseSettings

.. autopydantic_model:: smarter.common.conf.settings.email.EmailSettings

.. autopydantic_model:: smarter.common.conf.settings.features.FeatureSettings

.. autopydantic_model:: smarter.common.conf.settings.integrations.IntegrationSettings

.. autopydantic_model:: smarter.common.conf.settings.llm.LLMSettings

.. autopydantic_model:: smarter.common.conf.settings.project.ProjectSettings

.. autopydantic_model:: smarter.common.conf.settings.security.SecuritySettings

.. autopydantic_model:: smarter.common.conf.settings.tasks.TaskSettings

Helpers
-------

.. automodule:: smarter.common.conf.util
   :members:

.. automodule:: smarter.common.conf.credentials
   :members:

The environment
---------------

.. automodule:: smarter.common.conf.const
   :members:

.. automodule:: smarter.common.conf.env
   :members:
