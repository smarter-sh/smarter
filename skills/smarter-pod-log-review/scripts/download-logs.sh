#!/usr/bin/env bash
# Download the logs of a deployed Smarter environment's running pods, and its inventory.
#
# Usage:
#   skills/smarter-pod-log-review/scripts/download-logs.sh <context> <namespace> <folder> [since]
#
# Examples:
#   download-logs.sh "$CTX" "$NS" "$SCRATCH/prod-logs"          # everything each container kept
#   download-logs.sh "$CTX" "$NS" "$SCRATCH/prod-logs" 25h      # the last 25 hours
#
# <folder> must not exist, or be empty: downloaded logs are untrusted data. It gets:
#   inventory/pods.txt        kubectl get pods -o wide
#   inventory/events.txt      kubectl get events, oldest first
#   inventory/describe.txt    kubectl describe pod, for each reviewed pod
#   inventory/images.txt      each deployment's ReplicaSets: created, replicas, image (the release)
#   <deployment>/<pod>.log            the pod's log, with timestamps
#   <deployment>/<pod>.previous.log   the log from before its last restart, if it restarted
#
# Every kubectl call goes through skills/smarter-kubectl/scripts/kubectl.sh, which runs only
# commands that read. Nothing is printed but counts and file names, so that the script can run
# in a public GitHub Actions log.

set -euo pipefail

if [ $# -lt 3 ]; then
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi

CTX="$1"
NS="$2"
OUT="$3"
SINCE="${4:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
KUBECTL="$HERE/../../smarter-kubectl/scripts/kubectl.sh"
DEPLOYMENTS=(smarter smarter-worker smarter-worker-infrastructure smarter-beat)

k() { "$KUBECTL" "$CTX" "$NS" "$@"; }

if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT")" ]; then
  echo "download-logs.sh: $OUT is not empty. Use a new folder." >&2
  exit 1
fi
mkdir -p "$OUT/inventory"

since=()
if [ -n "$SINCE" ]; then
  since=(--since="$SINCE")
fi

k get pods -o wide >"$OUT/inventory/pods.txt"
k get events --sort-by=.lastTimestamp >"$OUT/inventory/events.txt" 2>&1 || true
: >"$OUT/inventory/describe.txt"
: >"$OUT/inventory/images.txt"

total=0
for deployment in "${DEPLOYMENTS[@]}"; do
  pods=$(k get pods -l "app.kubernetes.io/name=$deployment" \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
  {
    echo "== $deployment"
    k get rs -l "app.kubernetes.io/name=$deployment" \
      -o jsonpath='{range .items[*]}{.metadata.creationTimestamp} {.spec.replicas} {.spec.template.spec.containers[0].image}{"\n"}{end}' |
      sort
  } >>"$OUT/inventory/images.txt"
  if [ -z "$pods" ]; then
    echo "$deployment: no pods"
    continue
  fi
  mkdir -p "$OUT/$deployment"
  count=0
  while IFS= read -r pod; do
    [ -n "$pod" ] || continue
    k describe pod "$pod" >>"$OUT/inventory/describe.txt"
    k logs "$pod" --all-containers --timestamps "${since[@]}" >"$OUT/$deployment/$pod.log" 2>&1 || true
    if ! k logs "$pod" --all-containers --timestamps --previous >"$OUT/$deployment/$pod.previous.log" 2>/dev/null; then
      rm -f "$OUT/$deployment/$pod.previous.log"
    fi
    count=$((count + 1))
  done <<<"$pods"
  total=$((total + count))
  echo "$deployment: $count pod(s), $(cat "$OUT/$deployment"/*.log | wc -l | tr -d ' ') log lines"
done

echo "downloaded the logs of $total pod(s) into $OUT"
