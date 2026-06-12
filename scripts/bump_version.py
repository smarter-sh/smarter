"""
Script to update the semantic version in pyproject.toml and Dockerfile.

Called automatically from semantic-release hooks.
see: release.config.js in the root directory.

1.) semantic-release will call this script with the new version as an
argument.

2.) .github/workflows/build.yml will call this script with the new
version and --cicd flag to update additional files for CI/CD integration.

    Usage:

    python scripts/bump_version.py <new_version>

Updates:
- smarter/smarter/__version__.py
- pyproject.toml
- Dockerfile
- helm/charts/smarter/Chart.yaml
- helm/charts/smarter/values.yaml
- .github/actions/deploy/action.yml
"""

import re
import sys
from pathlib import Path

PLACEHOLDER = "9999.9999.9999.dev9999"

# semantic version: ##.##.## or ##.##.##-label.n
SEMANTIC_VERSION_REGEX = r"^\d+\.\d+\.\d+(-[A-Za-z0-9.]+)?$"


def update_version_in_file(filepath, replacement):
    """
    Update the version in a file by replacing the placeholder with the new.

    version.

    .. args:
        filepath (str): The path to the file to update.
        replacement (str): The new version string to replace the placeholder.

    .. returns:
        None

    .. raises:
        ValueError: If the placeholder is not found in the file.
    """

    path = Path(filepath)
    text = path.read_text(encoding="utf-8")
    count = text.count(PLACEHOLDER)

    if count == 0:
        raise ValueError(f"Placeholder '{PLACEHOLDER}' not found in {filepath}")

    path.write_text(
        text.replace(PLACEHOLDER, replacement),
        encoding="utf-8",
    )

    print(f"Updated {filepath}: {count} replacements")


def main():
    """
    Main function to update version in multiple files.

    If --cicd flag is provided, it updates additional files for CI/CD
    integration.

    .. args:
        new_version (str): The new version to set, in format ##.##.## or ##.##.##-label.n
        --cicd (bool): If provided, also updates pyproject.toml, Dockerfile, GitHub Action, and Helm charts.

    .. returns:
        None

    .. raises:
        ValueError: If the new version format is invalid or if the placeholder
        is not found in any of the files.
    """
    cicd: bool = False
    usage: str = "Usage: python bump_version.py <new_version> [--cicd]"
    if len(sys.argv) not in (2, 3):
        print(usage)
        sys.exit(1)

    new_version = sys.argv[1]
    if not re.match(SEMANTIC_VERSION_REGEX, new_version):
        print("Error: Version must be in format ##.##.## or ##.##.##-label.n (e.g., 0.1.20 or 0.14.0-alpha.1)")
        sys.exit(1)

    if len(sys.argv) == 3:
        if sys.argv[2] != "--cicd":
            print(usage)
            sys.exit(1)
        cicd = True

    update_version_in_file("smarter/smarter/__version__.py", new_version)
    if cicd:
        update_version_in_file(
            "pyproject.toml",
            new_version,
        )
        update_version_in_file("Dockerfile", new_version)
        update_version_in_file(".github/actions/deploy/action.yml", new_version)
        update_version_in_file("helm/charts/smarter/values.yaml", new_version)
        update_version_in_file("helm/charts/smarter/Chart.yaml", new_version)


if __name__ == "__main__":
    main()
