"""Constants for the vectorstore app."""

import os

namespace = "vectorstore"
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
BUILTIN_VECTORSTORE_PATH = os.path.join(DATA_PATH, "vectorstores")
"""The built-in Vectorstore manifests, which ``manage.py add_builtin_vectorstores`` applies."""
PINECONE_API_KEY_SECRET_NAME = "pinecone_api_key"
PINECONE_CONNECTION_NAME = "pinecone"
PINECONE_API_URL = "https://api.pinecone.io"
QDRANT_CLOUD_API_KEY_SECRET_NAME = "qdrant_cloud_api_key"
QDRANT_CLOUD_CONNECTION_NAME = "qdrant_cloud"
