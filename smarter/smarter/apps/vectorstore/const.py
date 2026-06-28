"""Constants for the vectorstore app."""

import os

namespace = "vectorstore"
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
PINECONE_API_KEY_SECRET_NAME = "pinecone_api_key"
