"""Constants for the connection app."""

import os

namespace = "connection"
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = HERE
STACKADEMY_PATH = os.path.join(HERE, "data", "stackademy")
"""The Stackademy SqlConnection and ApiConnection manifests, which ``manage.py add_example_connections`` applies."""
