#!/usr/bin/env bash
# Report whether the committed api contract is stale: regenerate it in the smarter-app container,
# into a temporary folder, and diff it against the host's committed files. Writes nothing in the
# repository.
#
# usage, from the repository root, with the containers running the current code (make build && make run):
#   skills/smarter-api-contract/scripts/check-contract.sh
#
# exit status: 0 if the contract is current, 1 if it is stale, 2 if it could not be generated.
set -uo pipefail

CONTRACT="smarter/smarter/apps/api/v1/contract"
REMOTE="/tmp/api-contract-check"
LOCAL="$(mktemp -d)"
trap 'rm -rf "$LOCAL"' EXIT

docker exec smarter-app bash -c "rm -rf $REMOTE && mkdir -p $REMOTE/sam && cd /home/smarter_user/smarter && \
  python manage.py export_api_contract --sam-dir $REMOTE/sam --openapi $REMOTE/openapi.json > /dev/null 2>&1" \
  || { echo "export_api_contract failed in smarter-app" >&2; exit 2; }
docker cp -q "smarter-app:$REMOTE/." "$LOCAL/" || exit 2

stale=0
diff -q "$LOCAL/openapi.json" "$CONTRACT/openapi.json" > /dev/null || { echo "stale: openapi.json"; stale=1; }
for file in "$LOCAL"/sam/*.json; do
  name="$(basename "$file")"
  if [ ! -f "$CONTRACT/sam/$name" ]; then
    echo "missing: sam/$name"; stale=1
  elif ! diff -q "$file" "$CONTRACT/sam/$name" > /dev/null; then
    echo "stale: sam/$name"; stale=1
  fi
done
for file in "$CONTRACT"/sam/*.json; do
  [ -f "$LOCAL/sam/$(basename "$file")" ] || { echo "obsolete: sam/$(basename "$file")"; stale=1; }
done

if [ "$stale" -eq 0 ]; then
  echo "The api contract is current."
else
  echo "Run make api-contract, review the diff, and commit the files."
fi
exit "$stale"
