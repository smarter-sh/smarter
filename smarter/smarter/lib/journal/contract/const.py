"""Constants of the Smarter Journal api contract."""

import os

HERE = os.path.abspath(os.path.dirname(__file__))
SCHEMA_PATH = os.path.join(HERE, "journal-contract.schema.json")
"""The JSON Schema of the contract, generated from :mod:`smarter.lib.journal.contract.models`."""

JOURNAL_KEY_PATTERN = r"^[a-f0-9]{64}$"
"""The format of a journal entry's key: 64 hexadecimal characters, from ``hash_factory(length=64)``."""
