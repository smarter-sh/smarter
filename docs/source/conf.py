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
REPO_ROOT = os.path.abspath(os.path.join(SMARTER_ROOT, "../"))
sys.path.insert(0, SMARTER_ROOT)

import django
from dotenv import load_dotenv

from smarter.common.conf import smarter_settings
from smarter.common.const import (
    AUTHOR,
    SMARTER_ORGANIZATION_WEBSITE_URL,
    SMARTER_PRODUCT_NAME,
    SMARTER_PROJECT_WEBSITE_URL,
)
from smarter.common.exceptions import SmarterConfigurationError

# Load environment variables from .env file. This is necessary for the
# sphinx_contributors extension to access the GitHub token and fetch contributor information.
env_path = os.path.join(REPO_ROOT, ".env")
load_dotenv(env_path)

###############################################################################
# Smarter setup
###############################################################################
if not smarter_settings.environment:
    # shouldn't ever happen, but just in case.
    raise SmarterConfigurationError("The 'smarter_settings.environment' variable is not set.")

###############################################################################
# Django setup
###############################################################################
os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings.local"
contributors_github_token = os.environ.get("GITHUB_TOKEN")

django.setup()


###############################################################################
# Patch the get_field_type function in sphinxcontrib_django to be more robust
# and return "Unknown" instead of raising an exception when it encounters
# an issue.
###############################################################################
from sphinxcontrib_django.docstrings import classes, field_utils


def safe_get_field_type(field, include_role=True):
    """A safe wrapper around the original get_field_type function that returns.

    "Unknown" if any exception occurs.
    """

    try:
        rel = getattr(field, "remote_field", None)
        to = getattr(rel, "model", None) if rel else None
        if to is None:
            return "Unknown"
        return field_utils.get_field_type(field, include_role=include_role)
    # pylint: disable=broad-except
    except Exception:
        return "Unknown"


# patch BOTH
field_utils.get_field_type = safe_get_field_type
classes.get_field_type = safe_get_field_type

project = "Smarter Documentation"

# pylint: disable=redefined-builtin
copyright = f"2023 - {datetime.now().year}"
author = AUTHOR
release = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], text=True).strip()


try:
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("utf-8").strip()
# pylint: disable=broad-except
except Exception:
    commit = None


last_updated = datetime.now().strftime("%B-%Y")
html_extra_path = ["robots.txt", "llms.txt"]
# custom context variables to be used in Sphinx templates, presumably in
# the ./_templates/footer.html template override.
html_context = {
    # "commit": commit,
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
    "sphinx_contributors",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "sphinx_design",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_rtd_theme",
    "sphinx_sitemap",
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
autodoc_type_aliases = {
    "pydantic.types.JsonValue": "JsonValue",
    "JsonValue": "JsonValue",
}

# sitemap settings
html_baseurl = f"https://docs.{smarter_settings.root_domain}/"
sitemap_url_scheme = "{link}"
sitemap_filename = "sitemap.xml"
