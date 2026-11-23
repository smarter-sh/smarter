Overrides
=========

Django settings that the deployment passes to the process, which overwrite Smarter's in every
environment: ``DJANGO_*`` environment variables from the Helm chart's ``env`` on Kubernetes, and locally
from ``.env`` and the ``overrides/`` file that Docker Compose mounts. How to write them, and where
they go, is in :doc:`/smarter-platform/overrides`.

.. automodule:: smarter.settings.overrides
   :members:
   :show-inheritance:
