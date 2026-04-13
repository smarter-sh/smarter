# pylint: disable=C0413,C0411
"""
Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.abspath(os.path.dirname(__file__))
SMARTER_ROOT = os.path.abspath(os.path.join(HERE, "../../smarter"))
sys.path.insert(0, SMARTER_ROOT)

###############################################################################
# Smarter setup
###############################################################################
from smarter.__version__ import __version__  # noqa: F401
from smarter.common.conf import smarter_settings
from smarter.common.const import (
    SMARTER_ORGANIZATION_WEBSITE_URL,
    SMARTER_PRODUCT_NAME,
    SMARTER_PROJECT_WEBSITE_URL,
)

if not smarter_settings.environment:
    raise RuntimeError("The 'smarter_settings.environment' variable is not set.")

###############################################################################
# Django setup
###############################################################################
os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings.local"

import django

django.setup()


project = "Smarter Documentation"

# pylint: disable=redefined-builtin
copyright = f"{datetime.now().year}"
author = "Lawrence P. McDaniel - https://lawrencemcdaniel.com"
release = __version__

try:
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("utf-8").strip()
# pylint: disable=broad-except
except Exception:
    commit = None


last_updated = datetime.now().strftime("%Y-%m-%d")

# custom context variables to be used in Sphinx templates, presumably in
# the ./_templates/footer.html template override.
html_context = {
    "commit": commit,
    "last_updated": last_updated,
    "branding_company_name": smarter_settings.branding_corporate_name,
    "branding_smarter_product_name": SMARTER_PRODUCT_NAME,
    "smarter_project_web_site_url": SMARTER_PROJECT_WEBSITE_URL,
    "smarter_organization_web_site_url": SMARTER_ORGANIZATION_WEBSITE_URL,
}
# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib_django",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "sphinx_design",
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
autodoc_mock_imports = [
    "taggit",
    "cryptography.fernet",
    "django.conf",
    "django.contrib.auth.models",
    "django.core.validators",
    "django.core.handlers.wsgi",
    "django.db",
    "django.template.loader",
    "django.utils",
]
