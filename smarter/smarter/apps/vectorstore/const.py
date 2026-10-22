"""Constants for the vectorstore app."""

import os

namespace = "vectorstore"
HERE = os.path.abspath(os.path.dirname(__file__))
PINECONE_API_KEY_SECRET_NAME = "pinecone_api_key"
PINECONE_CONNECTION_NAME = "pinecone"
PINECONE_API_URL = "https://api.pinecone.io"
QDRANT_CLOUD_API_KEY_SECRET_NAME = "qdrant_cloud_api_key"
QDRANT_CLOUD_CONNECTION_NAME = "qdrant_cloud"
