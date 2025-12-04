Error Handling
================

Smarter Api Manifest (SAM) yaml manifest and Pydantic validation processing is handled in-line as part
of normal Smarter Api operations. Failures due to yaml parsing errors, Pydantic validation errors, missing
fields, or other manifest related issues are raised as exceptions that are caught and mapped in the
main Smarter Api error handling framework.


.. automodule:: smarter.lib.manifest.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
