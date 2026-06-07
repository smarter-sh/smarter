Smarter Development Framework
=============================

The Smarter :doc:`cloud-native <smarter-framework/technologies/kubernetes>` application framework consists fundamentally of a
set of software that spans the complete lifecycle of
cloud-native AI applications. The framework provides solutions for :doc:`cloud infrastructure <smarter-framework/technologies/aws>`,
:doc:`backend API services <smarter-framework/smarter-api>`,
and :doc:`frontend user interfaces <../smarter-framework/develop-reference/react-integration/smarter-chat>`. While the technologies and programming languages that we use to
implement these layers do certainly vary considerably, most of the
work of the Smarter Project consists of the backend API services, written in
:doc:`Python <smarter-framework/technologies/python>` on the :doc:`Django web framework <smarter-framework/developer-reference/lib/django>`,
:doc:`Django REST Framework (DRF) <smarter-framework/developer-reference/lib/drf>`, and :doc:`Pydantic <smarter-framework/technologies/pydantic>`,
leveraging the strengths of each to provide a robust and flexible foundation for building enterprise class applications.


.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-framework/getting-started
   smarter-framework/guides
   smarter-framework/smarter-manifests
   smarter-framework/smarter-api
   smarter-framework/smarter-cli
   smarter-framework/vs-code-extension
   smarter-framework/developer-reference
   smarter-framework/technologies
