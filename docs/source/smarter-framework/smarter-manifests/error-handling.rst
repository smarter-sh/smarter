SAM Error Handling
===================

Smarter API Manifest (SAM) yaml manifest and Pydantic validation processing is handled in-line as part
of normal Smarter API operations. Failures due to yaml parsing errors, Pydantic validation errors, missing
fields, or other manifest related issues are raised as exceptions that are caught and mapped in the
main Smarter API error handling framework.


.. automodule:: smarter.lib.manifest.exceptions
   :members:
   :undoc-members:
   :show-inheritance:
