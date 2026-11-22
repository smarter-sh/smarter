"""
The ids of the JSON Schemas that Smarter publishes: the contracts of its apis, the console and the journal.

A schema's ``$id`` names it, and the copies that the web console and the SDKs commit compare it, so it
is the same on every platform. It is not branding: an operator who rebrands the product, or serves
it from another domain, publishes the same schemas under the same ids.
"""

SMARTER_JSON_SCHEMA_BASE_URL = "https://smarter.sh/schemas"
"""The base of every Smarter JSON Schema's ``$id``."""


def smarter_schema_id(filename: str) -> str:
    """
    Return the ``$id`` of one of Smarter's JSON Schemas.

    **Example:**

    >>> smarter_schema_id("chat-contract.schema.json")
    'https://smarter.sh/schemas/chat-contract.schema.json'

    :param filename: The schema's file name.
    :returns: The schema's ``$id``.
    """
    return f"{SMARTER_JSON_SCHEMA_BASE_URL}/{filename}"
