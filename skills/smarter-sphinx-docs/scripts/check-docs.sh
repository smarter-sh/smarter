#!/usr/bin/env bash
# Check Sphinx pages without building the docs (a full build takes ~20 minutes):
#
# 1. every toctree entry and :doc: target names an existing .rst file,
# 2. every .. literalinclude:: / .. include:: target exists, and
# 3. every .. automodule:: / .. autoclass:: / ... target imports, with Django set
#    up, inside the smarter-app container (skipped when it is not running).
#
# usage, from the repository root:
#   skills/smarter-sphinx-docs/scripts/check-docs.sh [page.rst ...]
# e.g.
#   skills/smarter-sphinx-docs/scripts/check-docs.sh docs/source/smarter-resources/smarter-custom-domain.rst
#
# With no pages, every .rst file under docs/source is checked.
set -uo pipefail

SOURCE="docs/source"
if [ ! -d "$SOURCE" ]; then
  echo "Run this from the repository root." >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  pages=("$@")
else
  pages=()
  while read -r f; do pages+=("$f"); done < <(find "$SOURCE" -name '*.rst' | sort)
fi

status=0

echo "== links"
for f in "${pages[@]}"; do
  d=$(dirname "$f")
  while read -r p; do
    [ -z "$p" ] && continue
    case "$p" in
      /*) t="$SOURCE${p}.rst" ;;
      *) t="$d/$p.rst" ;;
    esac
    if [ ! -f "$t" ]; then
      echo "MISSING  $f: $p (expected $t)"
      status=1
    fi
  done < <(
  (
    # toctree entries are "target" or "Title <target>", with or without .rst; skip external urls.
    awk '/^\.\. toctree::/{t=1;next} t&&/^[^ ]/{t=0} t&&/^ +[^ :]/{print}' "$f" |
      sed -E 's/^ +//; s/^.*<([^>]*)>$/\1/' | grep -v '://' | grep -vx 'self'
    grep -o ':doc:`[^`]*`' "$f" | sed -E 's/:doc:`([^<`]*<)?([^>`]*)>?`/\2/'
  ) | sed -E 's/\.rst$//')
done
[ "$status" -eq 0 ] && echo "ok"

# Example manifests are included from /_example-manifests/, a shallow clone of
# smarter-sh/example-manifests that docs/source/conf.py makes at build time.
# Make the same clone here when it's missing, so those includes resolve.
if [ ! -d "$SOURCE/_example-manifests" ]; then
  git clone --depth 1 --quiet https://github.com/smarter-sh/example-manifests "$SOURCE/_example-manifests" ||
    echo "warning: could not clone smarter-sh/example-manifests; its includes will be reported missing" >&2
fi

echo "== includes"
include_status=0
for f in "${pages[@]}"; do
  d=$(dirname "$f")
  while read -r p; do
    [ -z "$p" ] && continue
    case "$p" in
      /*) t="$SOURCE${p}" ;;
      *) t="$d/$p" ;;
    esac
    if [ ! -f "$t" ]; then
      echo "MISSING  $f: $p (expected $t)"
      include_status=1
    fi
  done < <(grep -oE '^[[:space:]]*\.\. (literalinclude|include)::[[:space:]]*[^[:space:]]+' "$f" | awk '{print $NF}')
done
[ "$include_status" -eq 0 ] && echo "ok"
[ "$include_status" -ne 0 ] && status=1

echo "== autodoc targets"
targets=$(grep -ho '^\.\. auto\(module\|class\|function\|method\|attribute\|data\|pydantic_model\)::[[:space:]]*[^[:space:]]*' "${pages[@]}" |
  awk '{print $NF}' | sort -u)
if [ -z "$targets" ]; then
  echo "none"
elif ! docker ps --format '{{.Names}}' | grep -qx smarter-app; then
  echo "skipped: smarter-app is not running"
else
  # manage.py shell sets up Django with the container's settings module.
  code='
import importlib, os
bad = 0
for target in os.environ["AUTODOC_TARGETS"].split():
    try:
        importlib.import_module(target)
        continue
    except ImportError:
        pass
    try:
        module, _, name = target.rpartition(".")
        getattr(importlib.import_module(module), name)
    except Exception as e:
        bad += 1
        print("BROKEN  " + target + ": " + str(e))
print("ok" if not bad else str(bad) + " broken")
'
  output=$(docker exec -e AUTODOC_TARGETS="$targets" -e CODE="$code" smarter-app \
    bash -c 'cd /home/smarter_user/smarter && python manage.py shell -c "$CODE"' 2>/dev/null | grep -E '^(BROKEN|ok$|[0-9]+ broken$)')
  echo "$output"
  if [ "$output" != "ok" ]; then
    status=1
  fi
fi

exit "$status"
