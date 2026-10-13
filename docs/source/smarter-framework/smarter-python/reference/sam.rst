..
   Generated from the smarter-python SDK's docstrings by its scripts/generate_reference.py.
   Do not edit: change the docstring in https://github.com/smarter-sh/smarter-python, and regenerate.

SAM Models
==========

``smarter.models.sam``
----------------------

.. py:module:: smarter.models.sam

Typed models of every SAM (Smarter Application Manifest) kind, generated from the Smarter platform's JSON Schemas.

Each model describes a complete manifest of its kind: ``apiVersion``, ``kind``, ``metadata``,
``spec`` and the read-only ``status``. Use them to build manifests in code, with your editor's
completion and Pydantic's validation, or to read a described manifest with typed fields:

.. code-block:: python

    from smarter.models.sam import SAMGuardrail, sam_model

    manifest = client.guardrails.describe("pii_redactor")
    guardrail = manifest.to_sam()                  # a SAMGuardrail
    print(guardrail.spec.config.action)

The models keep fields that they don't declare, so that a manifest of a newer platform still
parses. The platform's own models also enforce business rules that a JSON Schema can't express:
validate a manifest with :meth:`smarter.resources.manifests.Manifests.validate` before you rely on it.

Do not edit: run ``scripts/generate_sam_models.py``.

.. py:data:: SAM_MODELS

   The model of each kind, by its manifest ``kind``.

.. py:function:: sam_model(kind: str) -> Type[smarter.models.sam.base.SAMModel]

   The model of a kind.

   :param kind: The manifest kind, e.g. ``LLMClient``.
   :returns: The model, e.g. :class:`SAMLLMClient`.
   :raises KeyError: If the SDK has no model of the kind.

``smarter.models.sam.base``
---------------------------

.. py:module:: smarter.models.sam.base

The base class of the generated SAM models.

.. py:class:: SAMModel

   Bases: :class:`smarter.models.base.SmarterModel`

   The base class of the generated SAM models: a :class:`~smarter.models.base.SmarterModel`, which keeps unknown fields.

   Its fields keep the manifest's own names, e.g. ``apiVersion`` and ``recordLocator``.

   Its regular expressions use Python's ``re``, because the platform's schemas include patterns
   with look-ahead (e.g. Pydantic's own pattern of a ``Decimal``), which Pydantic's default engine
   doesn't support. The generated fields' docstrings, which come from the platform's field
   descriptions, are their Pydantic descriptions too (``use_attribute_docstrings``).

   .. py:method:: to_manifest_dict() -> dict

      The manifest as a dict, without its read-only ``status``, ready to apply.

      :returns: The manifest.


   .. py:method:: to_yaml(status: Optional[bool] = False) -> str

      The manifest as YAML text.

      :param status: True to include the read-only ``status``.
      :returns: The YAML text.



.. toctree::
   :maxdepth: 1
   :caption: Kinds

   sam/account
   sam/apiconnection
   sam/apiplugin
   sam/budget
   sam/customdomain
   sam/guardrail
   sam/imagesearchplugin
   sam/llmclient
   sam/llmhost
   sam/llmhostcompute
   sam/mcpclient
   sam/orchestrator
   sam/plugin
   sam/prompt
   sam/provider
   sam/proxy
   sam/secret
   sam/skillplugin
   sam/smarterauthtoken
   sam/sqlconnection
   sam/sqlplugin
   sam/user
   sam/vectorsearch
   sam/vectorstore
   sam/websearchplugin
