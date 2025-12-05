# pylint: disable=C0413,C0411
"""
Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import datetime

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys


sys.path.insert(0, os.path.abspath("../../smarter"))

from smarter.__version__ import __version__  # noqa: F401
from smarter.common.conf import settings as smarter_settings


if not smarter_settings.environment:
    raise RuntimeError("The 'smarter_settings.environment' variable is not set.")

os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings." + smarter_settings.environment

import django


django.setup()


project = "Smarter Documentation"

# pylint: disable=redefined-builtin
copyright = f"{datetime.datetime.now().year}, The Smarter Project"
author = "Lawrence McDaniel"
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib_django",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_rtd_theme",
]

templates_path = ["_templates"]
exclude_patterns = []
django_settings = "smarter.settings.prod"
todo_include_todos = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/5.2/", "https://docs.djangoproject.com/en/5.2/_objects/"),
}
rst_epilog = f"""
.. |project_version| replace:: {release}
"""

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
}
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
]
