#!/usr/bin/env bash
# Check Sphinx pages without building the docs (a full build takes ~20 minutes):
#
# 1. every toctree entry and :doc: target names an existing .rst file, and
# 2. every .. automodule:: / .. autoclass:: / ... target imports, with Django set
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
