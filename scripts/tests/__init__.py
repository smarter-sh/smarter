"""
Tests of the workflows' scripts in scripts/.

They need only the standard library, and never call Slack, GitHub, Claude or a cluster. Run them
from the repository's root, with scripts/ as the top-level folder, so that they import the scripts
by name:

    python -m unittest discover -s scripts/tests -t scripts
"""
