"""Constants for Vectorstore manifest models."""

from smarter.lib.journal.enum import SmarterJournalThings

MANIFEST_KIND = SmarterJournalThings.VECTORSTORE.value

DEFAULT_QDRANT_IMAGE = "qdrant/qdrant:v1.19.1"
"""The Qdrant server image of a self-hosted database.

It matches the version of qdrant-client.
"""
DEFAULT_STORAGE = "10Gi"
DEFAULT_CPU = "500m"
DEFAULT_MEMORY = "1Gi"
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_BATCH_SIZE = 64
DEFAULT_SNAPSHOT_INTERVAL_HOURS = 24
DEFAULT_SNAPSHOT_RETENTION = 7
MAX_DIMENSION = 20000

__all__ = ["MANIFEST_KIND"]
