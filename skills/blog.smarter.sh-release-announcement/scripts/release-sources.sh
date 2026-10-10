#!/usr/bin/env bash
# Print the source material for a release announcement: the full message of
# every commit that a changelog file links to, once each, oldest first.
#
# Changelog entries are one-line commit subjects. The commit bodies explain
# what each change is, why it exists, its limits and its upgrade steps, which
# is what the blog post needs.
#
# usage, from the repository root:
#   skills/blog.smarter.sh-release-announcement/scripts/release-sources.sh changelogs/CHANGELOG-v0.16.md
set -euo pipefail

CHANGELOG="${1:-}"
if [ -z "$CHANGELOG" ] || [ ! -f "$CHANGELOG" ]; then
  echo "usage: $0 changelogs/CHANGELOG-vX.Y.md" >&2
  exit 1
fi

# Commit links look like (https://github.com/smarter-sh/smarter/commit/<sha>)
grep -oE '/commit/[0-9a-f]{7,40}' "$CHANGELOG" | sed 's|/commit/||' | awk '!seen[$0]++' |
  while read -r sha; do
    if ! git cat-file -e "${sha}^{commit}" 2>/dev/null; then
      echo "=== $sha (not in this clone; git fetch, then run again)"
      continue
    fi
    printf '%s %s\n' "$(git log -1 --format=%ct "$sha")" "$sha"
  done | sort -n | while read -r _ sha; do
    if [ "$_" = "===" ]; then echo "=== $sha"; continue; fi
    echo "================================================================"
    git log -1 --format='commit %h  %ad%n%n%B' --date=short "$sha"
    git show --stat --format= "$sha" | tail -1
    echo
  done
