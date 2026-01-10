import importlib
import os
import re
import sys


# Set up sys.path as in your conf.py
HERE = os.path.abspath(os.path.dirname(__file__))
SMARTER_ROOT = os.path.abspath(os.path.join(HERE, "smarter"))
sys.path.insert(0, SMARTER_ROOT)

# Collect all autodoc paths from .rst files
autodoc_pattern = re.compile(r"\.\. auto(?:class|module|function|method|attribute|data)::\s+([^\s]+)")
rst_dir = os.path.join(HERE, "docs/source")
broken = []

for root, _, files in os.walk(rst_dir):
    for fname in files:
        if fname.endswith(".rst"):
            with open(os.path.join(root, fname)) as f:
                for line in f:
                    m = autodoc_pattern.search(line)
                    if m:
                        path = m.group(1)
                        # Try to import the object/module
                        try:
                            if "." in path:
                                mod, obj = path.rsplit(".", 1)
                                imported = importlib.import_module(mod)
                                getattr(imported, obj)
                            else:
                                importlib.import_module(path)
                        except Exception as e:
                            broken.append((path, str(e)))

if broken:
    print("Broken autodoc paths:")
    for path, err in broken:
        print(f"{path}: {err}")
else:
    print("All autodoc paths imported successfully.")
