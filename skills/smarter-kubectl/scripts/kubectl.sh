#!/usr/bin/env bash
# Run one read-only kubectl command against a context and namespace.
#
# Usage:
#   skills/smarter-kubectl/scripts/kubectl.sh <context> <namespace> <kubectl command and args...>
#
# Examples:
#   kubectl.sh "$CTX" "$NS" get pods -o wide
#   kubectl.sh "$CTX" "$NS" describe pod smarter-worker-abc12-xyz34
#   kubectl.sh "$CTX" "$NS" logs smarter-beat-abc12-xyz34 --timestamps > <folder>/smarter-beat.log
#   kubectl.sh "$CTX" "$NS" get nodes
#
# It passes --context and -n to kubectl rather than switching the current context, so the user's
# own kubectl keeps pointing where it was. It runs only commands that read. For anything else it
# prints the command for the user to run, and exits 2. `exec` runs only when
# SMARTER_KUBECTL_ALLOW_EXEC=1 is set, which an agent sets only after the user said yes to that
# exec.

set -euo pipefail

if [ $# -lt 3 ]; then
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
fi

CTX="$1"
NS="$2"
shift 2
VERB="$1"
SUB="${2:-}"

refuse() {
  echo "kubectl.sh: refused, $1. For the user to run:" >&2
  shift
  printf '  kubectl --context %q -n %q' "$CTX" "$NS" >&2
  printf ' %q' "$@" >&2
  echo >&2
  exit 2
}

case "$VERB" in
get | describe | logs | top | events | explain | api-resources | api-versions | version) ;;
auth) [ "$SUB" = "can-i" ] || refuse "only 'auth can-i' reads" "$@" ;;
rollout) [ "$SUB" = "history" ] || [ "$SUB" = "status" ] || refuse "only 'rollout history|status' read" "$@" ;;
exec) [ "${SMARTER_KUBECTL_ALLOW_EXEC:-}" = "1" ] || refuse "exec needs the user's OK (SMARTER_KUBECTL_ALLOW_EXEC=1)" "$@" ;;
*) refuse "'$VERB' is not a read-only command" "$@" ;;
esac

exec kubectl --context "$CTX" -n "$NS" "$@"
