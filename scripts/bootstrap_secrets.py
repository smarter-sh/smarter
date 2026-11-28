#!/usr/bin/env python3
"""Write the platform's bootstrap secrets, one file per Smarter Secret, into ``bootstrap-secrets/`` (issue #1099).

Usage::

    python3 -I scripts/bootstrap_secrets.py                 # from the environment (CI's test workflow)
    python3 -I scripts/bootstrap_secrets.py --env-file .env # from a developer's .env (make bootstrap-secrets)

The keys of the built-in Providers, the search plugins and the managed vector databases reach the platform as
Smarter Secrets, never as environment variables. ``manage.py initialize_bootstrap_secrets``, which
``initialize_platform`` runs, turns each file of its folder into the Smarter admin's Secret of the file's name. On
Kubernetes the folder is the chart's Kubernetes Secret ``smarter-bootstrap-secrets``, built from its
``bootstrapSecrets`` values. Locally it is this repository's ``bootstrap-secrets/``, which is gitignored and mounted,
read-only, into ``smarter-api`` only, at the same path as on Kubernetes.

This script fills that folder from the variables that used to carry the keys, by the names in VARIABLES, e.g.
``SMARTER_APP_PROVIDER_OPENAI_API_KEY`` becomes ``bootstrap-secrets/openai_api_key``. Google's service account
arrives base64 encoded, and its file holds the decoded json. An empty variable or a placeholder (``SET-ME-...``) is
left out. The script prints only names, never a value.

It exits with 1 when the Google service account isn't valid base64.
"""

import argparse
import base64
import binascii
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPOSITORY_ROOT / "bootstrap-secrets"
PLACEHOLDER_PREFIX = "SET-ME"

VARIABLES = {
    "SMARTER_APP_LLMTOOL_BRAVE_SEARCH_API_KEY": "brave_search_api_key",
    "SMARTER_APP_LLMTOOL_TAVILY_API_KEY": "tavily_api_key",
    "SMARTER_APP_PROVIDER_ANTHROPIC_API_KEY": "anthropic_api_key",
    "SMARTER_APP_PROVIDER_COHERE_API_KEY": "cohere_api_key",
    "SMARTER_APP_PROVIDER_FIREWORKS_API_KEY": "fireworks_api_key",
    "SMARTER_APP_PROVIDER_GEMINI_API_KEY": "gemini_api_key",
    "SMARTER_APP_PROVIDER_GOOGLE_MAPS_API_KEY": "google_maps_api_key",
    "SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64": "google_service_account",
    "SMARTER_APP_PROVIDER_LLAMA_API_KEY": "llama_api_key",
    "SMARTER_APP_PROVIDER_MISTRAL_API_KEY": "mistral_api_key",
    "SMARTER_APP_PROVIDER_OPENAI_API_KEY": "openai_api_key",
    "SMARTER_APP_PROVIDER_TOGETHERAI_API_KEY": "togetherai_api_key",
    "SMARTER_APP_VECTORSTORE_PINECONE_API_KEY": "pinecone_api_key",
    "SMARTER_APP_VECTORSTORE_QDRANT_CLOUD_API_KEY": "qdrant_cloud_api_key",
}
"""Each variable that used to carry a key, and the Smarter Secret that holds it now."""

BASE64_VARIABLES = ("SMARTER_APP_PROVIDER_GOOGLE_SERVICE_ACCOUNT_B64",)
"""The variables whose value is base64 encoded.

Their Secret holds the decoded text.
"""


def read_env_file(path: Path) -> dict[str, str]:
    """The ``NAME=value`` lines of a .env file, without comments, blank lines or the value's quotes."""
    variables = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        variables[name] = value
    return variables


def is_set(value: str) -> bool:
    """Whether a variable's value is a key: neither empty nor a placeholder."""
    if not value:
        return False
    if value.startswith(PLACEHOLDER_PREFIX):
        return False
    return True


def bootstrap_secrets(variables: dict[str, str]) -> dict[str, str]:
    """The bootstrap secrets, by Secret name, from the variables that are set.

    :param variables: Variables by name, e.g. ``os.environ`` or a .env file's.
    :returns: Each Secret's value, by its name.
    :raises ValueError: if a base64 encoded value isn't valid base64.
    """
    secrets = {}
    for variable, secret_name in VARIABLES.items():
        value = variables.get(variable, "").strip()
        if not is_set(value):
            continue
        if variable in BASE64_VARIABLES:
            try:
                value = base64.b64decode(value, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError) as e:
                raise ValueError(f"{variable} isn't valid base64: {type(e).__name__}") from e
        secrets[secret_name] = value
    return secrets


def write_secrets(secrets: dict[str, str], out_dir: Path) -> None:
    """Write each Secret into a file of its name, readable by the container's user.

    The container's user isn't the host's, so the files are world readable, in a folder that only this
    repository's checkout holds.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, value in secrets.items():
        path = out_dir / name
        path.write_text(value, encoding="utf-8")
        path.chmod(0o644)


def main(argv: list[str]) -> int:
    """Write the bootstrap secrets from the environment, or from a .env file."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env-file", type=Path, help="Read the variables from this .env file, not the environment.")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="The folder to write. bootstrap-secrets/ by default.")
    args = parser.parse_args(argv)
    if args.env_file:
        variables = read_env_file(args.env_file)
    else:
        variables = dict(os.environ)
    try:
        secrets = bootstrap_secrets(variables)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    write_secrets(secrets, args.out)
    names = ", ".join(sorted(secrets)) or "none"
    print(f"Wrote the bootstrap secrets {names} into {args.out}.")
    if args.env_file and secrets:
        print(f"You can delete their variables from {args.env_file}: no service reads them any more.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
