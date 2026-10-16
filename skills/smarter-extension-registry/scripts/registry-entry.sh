#!/usr/bin/env bash
# Write the registry entry of a Smarter Extension's GitHub release, extensions/<slug>/<version>.yaml
# in a local checkout of smarter-sh/extensions-registry, and validate the registry. Downloads only
# the release's public assets from github.com. Never runs git write commands.
#
# usage, from the repository root:
#   skills/smarter-extension-registry/scripts/registry-entry.sh <extension-repo-dir> [version]
#
# version defaults to the newest v* tag on the extension's origin. The registry checkout defaults to
# ../extensions-registry; set REGISTRY_DIR to use another. PUBLISHER defaults to smarter-sh.
#
# exit status: 0 if the entry was written and the registry is valid, 1 otherwise.
set -euo pipefail

EXTENSION_DIR="${1:?usage: registry-entry.sh <extension-repo-dir> [version]}"
VERSION="${2:-}"
REGISTRY_DIR="${REGISTRY_DIR:-$(git rev-parse --show-toplevel)/../extensions-registry}"
PUBLISHER="${PUBLISHER:-smarter-sh}"

[ -f "$EXTENSION_DIR/pyproject.toml" ] || { echo "no pyproject.toml in $EXTENSION_DIR" >&2; exit 1; }
[ -f "$REGISTRY_DIR/scripts/validate.py" ] || { echo "no registry checkout at $REGISTRY_DIR" >&2; exit 1; }

SLUG="$(python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["tool"]["smarter"]["slug"])' \
  "$EXTENSION_DIR/pyproject.toml")"
REPO_URL="$(git -C "$EXTENSION_DIR" remote get-url origin)"
REPO_URL="${REPO_URL%.git}"
REPO_URL="${REPO_URL/git@github.com:/https://github.com/}"

if [ -z "$VERSION" ]; then
  VERSION="$(git -C "$EXTENSION_DIR" ls-remote --tags --refs origin 'v*' | sed 's|.*refs/tags/v||' | sort -V | tail -1)"
  [ -n "$VERSION" ] || { echo "no v* tags on $REPO_URL" >&2; exit 1; }
fi

ENTRY="$REGISTRY_DIR/extensions/$SLUG/$VERSION.yaml"
[ -e "$ENTRY" ] && { echo "$ENTRY already exists: a released version is never changed" >&2; exit 1; }

ARCHIVE="$SLUG-$VERSION.zip"
ARCHIVE_URL="$REPO_URL/releases/download/v$VERSION/$ARCHIVE"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

curl -sSfL -o "$WORK/$ARCHIVE" "$ARCHIVE_URL" \
  || { echo "no release asset at $ARCHIVE_URL: did the release workflow publish v$VERSION?" >&2; exit 1; }
SHA256="$(shasum -a 256 "$WORK/$ARCHIVE" | cut -d ' ' -f 1)"
if curl -sSfL -o "$WORK/$ARCHIVE.sha256" "$ARCHIVE_URL.sha256"; then
  [ "$(cut -d ' ' -f 1 "$WORK/$ARCHIVE.sha256")" = "$SHA256" ] \
    || { echo "$ARCHIVE does not match its attached .sha256" >&2; exit 1; }
else
  echo "warning: no $ARCHIVE.sha256 on the release; using the computed sha256" >&2
fi

mkdir -p "$(dirname "$ENTRY")"
cat > "$ENTRY" <<EOF
slug: $SLUG
version: $VERSION
publisher: $PUBLISHER
archive_url: $ARCHIVE_URL
sha256: $SHA256
EOF
echo "wrote $ENTRY"
cat "$ENTRY"

if ! (cd "$REGISTRY_DIR" && python3 scripts/validate.py --all); then
  rm -f "$ENTRY"
  echo "the registry did not validate; removed $ENTRY" >&2
  exit 1
fi
