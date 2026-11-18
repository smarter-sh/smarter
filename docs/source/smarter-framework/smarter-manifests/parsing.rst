Parsing a Manifest
==================

A manifest arrives as text: a file, a request body, or a string that an extension or a management
command passes on. ``parse_manifest()`` turns that text, YAML or JSON, into a dict, and
``read_manifest_file()`` does the same for a file. YAML is a superset of JSON, so one parser reads
both.

Parsing checks only that the text is a YAML object. Whether the object is a valid manifest, with an
``apiVersion``, a ``kind``, ``metadata`` and a ``spec`` of the right types, is decided by the kind's
Pydantic model, which reports every problem at once.

.. code-block:: python

    from smarter.apps.guardrail.manifest.models.guardrail.model import SAMGuardrail
    from smarter.lib.manifest.parsing import read_manifest_file

    data = read_manifest_file("path/to/guardrail.yaml")
    manifest = SAMGuardrail.model_validate(data)

Text that is not YAML, or YAML that is not an object, e.g. a list, raises
``SAMValidationError``, which the api returns to the client as a 400.

.. automodule:: smarter.lib.manifest.parsing
   :members:
