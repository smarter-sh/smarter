Smarter Development Framework
=============================

The Smarter :doc:`cloud-native <smarter-framework/kubernetes>` application framework consists fundamentally of a
set of software that spans the complete lifecycle of
cloud-native AI applications. The framework provides solutions for :doc:`cloud infrastructure <smarter-framework/aws>`,
:doc:`backend API services <smarter-framework/smarter-api>`,
and :doc:`frontend user interfaces <smarter-framework/react-integration/smarter-chat>`. While the technologies and programming languages that we use to
implement these layers do certainly vary considerably, most of the
work of the Smarter Project consists of the backend API services, written in
:doc:`Python <smarter-framework/python>` on the :doc:`Django web framework <smarter-framework/lib/django>`,
:doc:`Django REST Framework (DRF) <smarter-framework/lib/django/drf>`, and :doc:`Pydantic <smarter-framework/pydantic>`,
leveraging the strengths of each to provide a robust and flexible foundation for building enterprise class applications.


.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-framework/getting-started
   smarter-framework/guides
   smarter-framework/aws
   smarter-framework/docker
   smarter-framework/kubernetes
   smarter-framework/lib
   smarter-framework/python
   smarter-framework/pydantic
   smarter-framework/smtp
   smarter-framework/react-integration
   smarter-framework/smarter-api
   smarter-framework/smarter-cli
   smarter-framework/smarter-dashboard
   smarter-framework/smarter-enum
   smarter-framework/smarter-devops
   smarter-framework/smarter-journal
   smarter-framework/smarter-mixins
   smarter-framework/smarter-settings
   smarter-framework/smarter-utils
   smarter-framework/vs-code-extension
