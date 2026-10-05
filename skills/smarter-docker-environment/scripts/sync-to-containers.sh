#!/usr/bin/env bash
# Copy the host's changed Python, YAML, JSON and template files under
# smarter/smarter into the Smarter containers, then restart them and wait
# until the dev server answers.
#
# The containers have no bind mount of the source, so this is how edits
# reach them. Only files whose md5 differs are copied, one file at a time
# (copying a directory into an existing one nests it), and their ownership
# is fixed afterwards (docker cp writes root-owned files).
#
# usage, from the repository root:
#   skills/smarter-docker-environment/scripts/sync-to-containers.sh [subpath ...]
# e.g.
#   skills/smarter-docker-environment/scripts/sync-to-containers.sh apps/llmclient lib/unittest
#
# With no subpath, all of smarter/smarter is compared. It never deletes
# anything in a container: files that exist only there are left alone.
set -euo pipefail

HOST_ROOT="smarter/smarter"
CONTAINER_ROOT="/home/smarter_user/smarter/smarter"
CONTAINERS=(smarter-app smarter-worker smarter-worker-infrastructure smarter-beat)
SUBPATHS=("${@:-.}")

if [ ! -d "$HOST_ROOT" ]; then
  echo "Run this from the repository root." >&2
  exit 1
fi

for container in "${CONTAINERS[@]}"; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$container"; then
    echo "skipping $container: not running"
    continue
  fi
  changed=()
  while read -r f; do
    rel="${f#"$HOST_ROOT"/}"
    host_md5=$(md5 -q "$f" 2>/dev/null || md5sum "$f" | cut -d' ' -f1)
    container_md5=$(docker exec "$container" md5sum "$CONTAINER_ROOT/$rel" 2>/dev/null | cut -d' ' -f1 || true)
    if [ "$host_md5" != "$container_md5" ]; then
      changed+=("$rel")
    fi
  done < <(for p in "${SUBPATHS[@]}"; do
    find "$HOST_ROOT/$p" -type f \( -name '*.py' -o -name '*.yaml' -o -name '*.json' -o -name '*.html' -o -name '*.txt' \) \
      -not -path '*/__pycache__/*' -not -path '*/node_modules/*'
  done)

  echo "$container: ${#changed[@]} changed file(s)"
  for rel in ${changed[@]+"${changed[@]}"}; do
    docker exec -u root "$container" mkdir -p "$(dirname "$CONTAINER_ROOT/$rel")"
    docker cp "$HOST_ROOT/$rel" "$container:$CONTAINER_ROOT/$rel"
    echo "  $rel"
  done
  if [ "${#changed[@]}" -gt 0 ]; then
    docker exec -u root "$container" chown -R smarter_user "$CONTAINER_ROOT"
    docker restart "$container" >/dev/null
  fi
done

# Several copies in a row can kill smarter-app's auto-reloading dev server,
# which tests that apply manifests over HTTP depend on. Wait for it.
echo -n "waiting for http://localhost:9357/ "
for _ in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9357/ || true)
  if [ "$code" = "302" ] || [ "$code" = "200" ]; then
    echo "up ($code)"
    exit 0
  fi
  echo -n "."
  sleep 2
done
echo " not up after 2 minutes: check docker logs smarter-app" >&2
exit 1
