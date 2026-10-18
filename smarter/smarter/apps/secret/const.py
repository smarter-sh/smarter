"""Secret constants."""

import os

namespace = "secret"
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.abspath(os.path.join(HERE, "data"))
STACKADEMY_PATH = os.path.join(DATA_PATH, "stackademy")
"""The Stackademy Secrets, which ``manage.py add_example_secrets`` applies."""
