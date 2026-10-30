#!/usr/bin/env bash
# Copy the files that git sees as changed or new under smarter/smarter into every app container,
# fix their ownership, restart smarter-app, and wait for the dev server.
#
# Fast (seconds), because it copies only what git lists, rather than comparing every file's md5
# as sync-to-containers.sh does. Run it from anywhere:
#
#   skills/smarter-docker-environment/scripts/sync-changed-files.sh
#
# Written in bash, with a `while read` loop, on purpose: zsh does not word-split an unquoted
# $FILES, so `for f in $FILES` there runs once, with every path joined into one "file name", and
# docker cp fails (silently, if its errors are discarded).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
HOST_ROOT="smarter/smarter"
CONTAINER_ROOT="/home/smarter_user/smarter/smarter"
CONTAINERS=(smarter-app smarter-worker smarter-worker-infrastructure smarter-beat)

LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT
{
  git diff --name-only HEAD -- "$HOST_ROOT"
  git ls-files --others --exclude-standard -- "$HOST_ROOT"
} | grep -E '\.(py|yaml|yml|json|toml|md|rst|svg|html|txt|css|js|xml|po)$' | sort -u >"$LIST" || true

count=$(wc -l <"$LIST" | tr -d ' ')
echo "$count changed file(s)"
[ "$count" -eq 0 ] && exit 0

for container in "${CONTAINERS[@]}"; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
    echo "skipping $container: not running"
    continue
  fi
  failed=0
  while read -r f; do
    [ -f "$f" ] || continue # deleted files are left alone
    rel="${f#"$HOST_ROOT"/}"
    docker exec -u root "$container" mkdir -p "$(dirname "$CONTAINER_ROOT/$rel")"
    docker cp "$f" "$container:$CONTAINER_ROOT/$rel" || {
      echo "FAILED: $container $f"
      failed=1
    }
  done <"$LIST"
  docker exec -u root "$container" chown -R smarter_user "$CONTAINER_ROOT"
  echo "$container: synced$([ $failed -eq 1 ] && echo ', with failures')"
done

docker restart smarter-app >/dev/null
until [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:9357/)" = "302" ]; do sleep 2; done
echo "smarter-app is up"
