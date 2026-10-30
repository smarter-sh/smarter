#!/usr/bin/env bash
# Download the logs of a GitHub Actions run's failed jobs, and pull out their failures.
#
#   skills/smarter-ci-failures/scripts/fetch-run-logs.sh <run or job url, or run id> [output dir]
#
#   e.g. skills/smarter-ci-failures/scripts/fetch-run-logs.sh https://github.com/smarter-sh/smarter/actions/runs/41095264475
#
# For each failed job it writes <output dir>/<job id>.log (the whole log, without terminal colors) and
# <output dir>/<job id>.failures.txt (each Python unittest FAIL/ERROR block, the Python summary, and each
# Vitest failure), and prints the run's commit, its jobs, and the failures. The output dir defaults to a
# new temporary folder. A job url (.../job/<id>) fetches that job only, failed or not.
#
# It uses the gh cli. Without a gh login, it reads GH_TOKEN (or GITHUB_TOKEN) from the repository's .env,
# without printing it. GitHub's api sometimes answers 502 or 503; each call is retried.
set -euo pipefail

url="${1:?usage: fetch-run-logs.sh <run or job url, or run id> [output dir]}"
out="${2:-$(mktemp -d -t smarter-ci-XXXXXX)}"
mkdir -p "$out"
cd "$(git rev-parse --show-toplevel)"

repo="smarter-sh/smarter"
if [[ "$url" =~ github\.com/([^/]+/[^/]+)/actions/runs/([0-9]+)(/job/([0-9]+))? ]]; then
  repo="${BASH_REMATCH[1]}"
  run="${BASH_REMATCH[2]}"
  job="${BASH_REMATCH[4]:-}"
elif [[ "$url" =~ ^[0-9]+$ ]]; then
  run="$url"
  job=""
else
  echo "Not a GitHub Actions run url: $url" >&2
  exit 2
fi

if ! gh auth status >/dev/null 2>&1 && [ -z "${GH_TOKEN:-}" ] && [ -f .env ]; then
  GH_TOKEN="$(grep -E '^(GH_TOKEN|GITHUB_TOKEN)=' .env | head -1 | cut -d= -f2- | tr -d '"' || true)"
  export GH_TOKEN
fi

# gh api, retried: GitHub's api answers 502 and 503 now and then, the run's logs included.
api() {
  local attempt
  for attempt in 1 2 3 4 5; do
    if gh api --allow-escape-sequences "$@"; then
      return 0
    fi
    echo "  (gh api $1 failed, attempt $attempt of 5; retrying)" >&2
    sleep $((attempt * 5))
  done
  return 1
}

# terminal colors, which the logs keep, and which gh refuses to print without --allow-escape-sequences.
strip_colors() { sed $'s/\x1b\\[[0-9;]*[A-Za-z]//g'; }

echo "Run $run of $repo:"
api "repos/$repo/actions/runs/$run" \
  --jq '"  \(.name), \(.event) on \(.head_branch) at \(.head_sha[0:9]): \(.conclusion // .status)\n  \(.html_url)"'
echo "  commit: $(api "repos/$repo/commits/$(api "repos/$repo/actions/runs/$run" --jq .head_sha)" --jq '.commit.message | split("\n")[0]')"
echo
echo "Jobs:"
api "repos/$repo/actions/runs/$run/jobs?per_page=100" --jq '.jobs[] | "  \(.conclusion // .status)\t\(.id)\t\(.name)"'

if [ -n "$job" ]; then
  jobs="$job"
else
  jobs="$(api "repos/$repo/actions/runs/$run/jobs?per_page=100" \
    --jq '.jobs[] | select(.conclusion == "failure" or .conclusion == "timed_out" or .conclusion == "cancelled") | .id')"
fi
if [ -z "$jobs" ]; then
  echo
  echo "No failed jobs."
  exit 0
fi

for id in $jobs; do
  log="$out/$id.log"
  failures="$out/$id.failures.txt"
  api "repos/$repo/actions/jobs/$id/logs" | strip_colors | cut -c30- >"$log"
  {
    # Python's unittest prints every FAIL and ERROR block together, just before its summary: print from the
    # first block's heading to the summary.
    awk '
      /^(FAIL|ERROR)( \[[0-9.]+s\])?: / { inblock = 1 }
      inblock { print }
      /^Ran [0-9]+ tests? in / { if (!inblock) print; inblock = 0 }
      /^(FAILED \(|OK$|OK \()/ { print }
    ' "$log"
    # Vitest, in a job that ran it: the failed tests, and each failure's heading and error.
    if grep -qE '^ *Test Files ' "$log"; then
      grep -nE '^ *× | FAIL  \||^ *(AssertionError|TestingLibraryElementError|TypeError|Error):|^ *Test Files |^ *Tests ' "$log" || true
    fi
    # The step that failed, if neither found anything.
    grep -nE '##\[error\]' "$log" || true
  } >"$failures"
  echo
  echo "=== job $id: $log"
  if [ -s "$failures" ]; then
    cat "$failures"
  else
    echo "(no unittest or vitest failure found: read the log's end)"
    tail -40 "$log"
  fi
done

echo
echo "Logs and failures are in $out"
