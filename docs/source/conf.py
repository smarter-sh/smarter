# pylint: disable=C0413,C0411
"""
Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import builtins
import importlib
import logging
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

# django.setup() applies Smarter's LOGGING, which sets the root logger to the
# app's log level (often DEBUG locally). Third-party loggers inherit it, so
# urllib3 would log every GitHub API request that sphinx_contributors makes.
# Sphinx's own logger does not propagate to root, so build output is unaffected.
logging.getLogger().setLevel(logging.WARNING)
for _noisy_logger in ("urllib3", "requests_cache", "github"):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)

###############################################################################
# Patch the get_field_type function in sphinxcontrib_django to be more robust
# and return "Unknown" instead of raising an exception when it encounters
# an issue.
###############################################################################
from pygments.lexer import inherit
from pygments.lexers.jsx import TsxLexer
from pygments.token import Keyword, Operator, Punctuation, Text, Whitespace
from sphinx.addnodes import pending_xref
from sphinx.domains.python import PythonDomain
from sphinx.util import logging as sphinx_logging
from sphinxcontrib_django.docstrings import classes, field_utils

# Import the guardrail services' Pydantic contracts before sphinx_autodoc_typehints resolves
# pydantic's type-checking-only imports, after which pydantic cannot build their models.
import smarter.apps.guardrail.services  # noqa: E402,F401  # pylint: disable=wrong-import-position,unused-import


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


###############################################################################
# Example manifests
#
# The example SAM manifests that the platform loads at initialization live in
# their own community repository, smarter-sh/example-manifests, not in this
# one. Pages show them with ``.. literalinclude:: /_example-manifests/<path>``,
# so make a shallow clone of that repository into docs/source/_example-manifests/
# (git-ignored, and excluded from the build's own sources). An existing clone
# is updated when possible and otherwise used as it is. If the clone fails,
# e.g. offline, log a warning and carry on: those includes then warn, but the
# rest of the build is unaffected.
###############################################################################
EXAMPLE_MANIFESTS_REPOSITORY_URL = "https://github.com/smarter-sh/example-manifests"
EXAMPLE_MANIFESTS_DIR = os.path.join(HERE, "_example-manifests")


def clone_example_manifests():
    """Make or update the shallow clone of smarter-sh/example-manifests that the docs include from."""
    git_dir = os.path.join(EXAMPLE_MANIFESTS_DIR, ".git")
    try:
        if os.path.isdir(git_dir):
            subprocess.run(["git", "-C", EXAMPLE_MANIFESTS_DIR, "pull", "--ff-only", "--quiet"], check=False)
        elif not os.path.exists(EXAMPLE_MANIFESTS_DIR):
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--quiet",
                    EXAMPLE_MANIFESTS_REPOSITORY_URL,
                    EXAMPLE_MANIFESTS_DIR,
                ],
                check=True,
            )
    # pylint: disable=broad-except
    except Exception as e:
        sphinx_logging.getLogger(__name__).warning(
            "docs.conf.clone_example_manifests() could not clone %s into %s: %s",
            EXAMPLE_MANIFESTS_REPOSITORY_URL,
            EXAMPLE_MANIFESTS_DIR,
            e,
        )


clone_example_manifests()


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
    "sphinx_design",
    "sphinx.ext.todo",
    "sphinx.ext.intersphinx",
    # napoleon must load before sphinx_autodoc_typehints, which otherwise parses
    # NumPy/Google sections as raw reST and reports "Unexpected indentation".
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_rtd_theme",
    "sphinx_sitemap",
]

templates_path = ["_templates"]
# sphinx_autodoc_typehints cannot resolve some type hints that third party packages, e.g.
# asgiref and pydantic, import only for type checking. These are harmless.
suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]
# _example-manifests is the clone of smarter-sh/example-manifests (see above), read only by literalinclude.
exclude_patterns = ["_example-manifests"]
django_settings = "smarter.settings.prod"
todo_include_todos = True
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": ("https://docs.djangoproject.com/en/5.2/", "https://docs.djangoproject.com/en/5.2/_objects/"),
    "cache_results": ("https://docs.cache-results.smarter.sh/", None),
    "smarter_python": ("https://docs.smarter-python.smarter.sh/", None),
    "smarter_types": ("https://docs.smarter-types.smarter.sh/", None),
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
# Smarter has no PEP 484 type comments. With this on, documenting an attribute
# of a Pydantic model, e.g. ListViewPagination.model_config, makes autodoc parse
# pydantic/main.py and write its annotations, as strings, into
# BaseModel.__annotations__, which Pydantic keeps empty. Every model with
# extra="allow" that's defined afterwards then fails to import with
# "The type annotation for `__pydantic_extra__` must be `dict[str, ...]`".
autodoc_use_type_comments = False

# sitemap settings
html_baseurl = f"https://docs.{smarter_settings.root_domain}/"
sitemap_url_scheme = "{link}"
sitemap_filename = "sitemap.xml"


###############################################################################
# Resolve builtin names in docstring fields, e.g. "sender (type)" or
# ":rtype: type[Foo]", to the Python builtin. Sphinx resolves these fields with
# a fuzzy search that matches any documented attribute ending in the same name,
# e.g. DNSRecord.type, and links there, or warns "more than one target found".
# Dropping refspecific makes Sphinx look for the exact name, which falls through
# to intersphinx.
###############################################################################
def resolve_builtins_exactly(app, doctree):  # pylint: disable=unused-argument
    """Make Python domain references to builtin names exact rather than fuzzy."""
    for node in doctree.findall(pending_xref):
        if node.get("refdomain") == "py" and node.get("reftarget") in vars(builtins):
            node.attributes.pop("refspecific", None)


###############################################################################
# Platform packages re-export their models, e.g.
# smarter.apps.llmclient.models.LLMClient, so the fuzzy search behind docstring
# type fields finds the same object under several names, warns "more than one
# target found", and links to either. Of a re-exported object's matches, keep
# the module that defines it. Fully qualified references are left alone. The
# smarter-python SDK's objects are on its own site, through intersphinx.
###############################################################################
def defining_name(names: list[str]) -> str | None:
    """Of several names of one platform object, the one in the module that defines it."""
    objects = []
    for name in names:
        module_name, _, attr = name.rpartition(".")
        try:
            objects.append(getattr(importlib.import_module(module_name), attr))
        # pylint: disable=broad-except
        except Exception:
            return None
    if any(obj is not objects[0] for obj in objects):
        return None
    module_name = getattr(objects[0], "__module__", None)
    return next((name for name in names if name.rpartition(".")[0] == module_name), None)


def disambiguate_reexports(find_obj):
    """Wrap PythonDomain.find_obj to narrow ambiguous matches; see the comment above."""

    def wrapper(
        self, env, modname, classname, name, type, searchmode=0
    ):  # pylint: disable=too-many-arguments,too-many-positional-arguments,redefined-builtin
        matches = find_obj(self, env, modname, classname, name, type, searchmode)
        if searchmode != 1 or len(matches) < 2:
            return matches
        defining = defining_name([match[0] for match in matches])
        if defining:
            matches = [match for match in matches if match[0] == defining]
        return matches

    return wrapper


PythonDomain.find_obj = disambiguate_reexports(PythonDomain.find_obj)


###############################################################################
# sphinxcontrib_django appends the pretty-printed value of every dict, list,
# tuple or set module constant to its docstring as a JavaScript code block,
# ignoring ":meta hide-value:". Remove that block when the constant asks for
# its value to be hidden, e.g. a dict of compiled regular expressions, whose
# value Pygments cannot lex and which leaks function memory addresses.
###############################################################################
def honor_hide_value(app, what, name, obj, options, lines):  # pylint: disable=unused-argument,too-many-arguments
    """Drop sphinxcontrib_django's value block from data marked ``:meta hide-value:``."""
    if what == "data" and ":meta hide-value:" in lines and ".. code-block:: JavaScript" in lines:
        del lines[lines.index(".. code-block:: JavaScript") :]


###############################################################################
# Pygments' TSX lexer reads a generic type argument, e.g.
# useState<Editor | null> or useRef<string[]>, as a JSX tag, and fails on the
# "|" or "[". It also fails on non-ASCII JSX text, e.g. "Loading…". Sphinx then
# warns that the literalincluded React components fail to highlight. A "<"
# directly after a name opens a type argument: Prettier puts a space before a
# JSX tag and around a less-than operator.
###############################################################################
class SmarterTsxLexer(TsxLexer):
    """Pygments' TSX lexer, plus generic type arguments and non-ASCII JSX text."""

    tokens = {
        "root": [
            (r"(?<=[\w$])<", Punctuation, "type-arguments"),
            inherit,
            (r"[^\x00-\x7f]+", Text),
        ],
        "type-arguments": [
            (r"<", Punctuation, "#push"),
            (r">", Punctuation, "#pop"),
            (r"=>", Operator),
            (r"\s+", Whitespace),
            (r"[\w$.]+", Keyword.Type),
            (r"[^\w\s$<>=]+|=", Punctuation),
        ],
    }


###############################################################################
# Sphinx reads sources in forked worker processes (-j auto), and
# sphinx_contributors calls the GitHub API while it reads contributors.rst. On
# macOS a network call in a child forked from a multi-threaded process crashes
# it (SIGSEGV in CoreFoundation), Sphinx silently drops the documents of every
# worker, and the build fails with "Sphinx is unable to load the master
# document". Read the pages that call the network in the main process, before
# the workers are forked, and hand them back to the builder afterwards so that
# they are still written.
###############################################################################
NETWORK_DOCNAMES = ("contributors",)
_docnames_read_before_fork = []


def read_network_docs_before_fork(app, env, docnames):
    """Read the pages that call the network in the main process, and remove them from ``docnames``."""
    _docnames_read_before_fork.clear()
    for docname in NETWORK_DOCNAMES:
        if docname in docnames:
            docnames.remove(docname)
            app.events.emit("env-purge-doc", env, docname)
            env.clear_doc(docname)
            app.builder.read_doc(docname)
            _docnames_read_before_fork.append(docname)


def return_network_docs(app, env):  # pylint: disable=unused-argument
    """Return the pages read before the fork, so that the builder writes them."""
    return list(_docnames_read_before_fork)


def setup(app):
    """Register this configuration's Sphinx event handlers."""
    app.connect("doctree-read", resolve_builtins_exactly)
    # sphinxcontrib_django's handler runs at the default priority, 500.
    app.connect("autodoc-process-docstring", honor_hide_value, priority=600)
    app.add_lexer("tsx", SmarterTsxLexer)
    app.connect("env-before-read-docs", read_network_docs_before_fork)
    app.connect("env-updated", return_network_docs)
