"""
Check that every autodoc target in the Sphinx documentation imports, without building the docs.

Finds the target of each ``.. automodule::``, ``.. autoclass::``, etc. directive in the .rst files
of docs/source, and imports it, with sys.path and Django set up as conf.py sets them up. Prints the
targets that fail to import, and exits with status 1 if there are any.

Usage, from the repository root, with the docs requirements installed::

    python docs/source/lint.py
"""

import importlib
import os
import re
import sys

# Set up sys.path and Django as conf.py does.
HERE = os.path.abspath(os.path.dirname(__file__))
SMARTER_ROOT = os.path.abspath(os.path.join(HERE, "../../smarter"))
sys.path.insert(0, SMARTER_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

import django  # noqa: E402

django.setup()

# Collect all autodoc paths from .rst files
autodoc_pattern = re.compile(
    r"^\.\. auto(?:module|class|function|method|attribute|data|exception|pydantic_model)::\s+(\S+)"
)
rst_dir = HERE
broken = []
targets = set()

for root, _, files in os.walk(rst_dir):
    for fname in files:
        if fname.endswith(".rst"):
            with open(os.path.join(root, fname), encoding="utf-8") as f:
                for line in f:
                    m = autodoc_pattern.search(line)
                    if m:
                        targets.add(m.group(1))

for path in sorted(targets):
    # Try to import the target as a module, and otherwise as an object in a module.
    try:
        importlib.import_module(path)
        continue
    except ImportError:
        pass
    try:
        mod, obj = path.rsplit(".", 1)
        getattr(importlib.import_module(mod), obj)
    except Exception as e:  # pylint: disable=broad-except
        broken.append((path, str(e)))

if broken:
    print("Broken autodoc paths:")
    for path, err in broken:
        print(f"{path}: {err}")
    sys.exit(1)
print(f"All {len(targets)} autodoc paths imported successfully.")
