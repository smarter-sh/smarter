"""
The Smarter api contract: the JSON Schemas of the SAM manifests, and the OpenAPI document of the cli api.

Both are generated from the platform's Pydantic models by ``manage.py export_api_contract``, and
committed beside this package: ``sam/<Kind>.schema.json`` and ``openapi.json``. Tests fail when a
committed file is out of date. They are the source from which the ``smarter`` cli and the SDKs
generate their clients, so a change to a SAM model is a change to the api.

See :doc:`The Api Contract </smarter-framework/smarter-api/api-contract>`.
"""
