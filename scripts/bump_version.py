"""
Script to update the semantic version in pyproject.toml and Dockerfile.

Called automatically from semantic-release hooks.
see: release.config.js in the root directory.

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


def update_version_in_file(filepath, replacement):

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
    cicd: bool = False
    usage: str = "Usage: python bump_version.py <new_version> [--cicd]"
    if len(sys.argv) not in (2, 3):
        print(usage)
        sys.exit(1)

    new_version = sys.argv[1]

    if len(sys.argv) == 3:
        if sys.argv[2] != "--cicd":
            print(usage)
            sys.exit(1)
        cicd = True

    # Validate semantic version: ##.##.## or ##.##.##-label.n
    if not re.match(r"^\d+\.\d+\.\d+(-[A-Za-z0-9.]+)?$", new_version):
        print("Error: Version must be in format ##.##.## or ##.##.##-label.n (e.g., 0.1.20 or 0.14.0-alpha.1)")
        sys.exit(1)

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
