"""
Smarter annotations: Kubernetes-style key-value metadata on every Smarter resource.

Every resource built on :class:`smarter.lib.django.models.MetaDataModel` has annotations, set
from its manifest's ``metadata.annotations``. Integrations use them to associate Smarter
resources with resources in their own systems, query them (:mod:`.selectors`,
:class:`.models.Annotation`), and react when they change (:mod:`.handlers`, :mod:`.signals`).
"""
