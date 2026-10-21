#!/usr/bin/env bash
# Report the local checkouts of The Smarter Project's other repositories, next to this one: each
# one's branch, uncommitted changes, and whether its commit is the remote's. Read-only: it runs
# git ls-remote, never git fetch, pull or checkout.
#
# usage, from the repository root:
#   skills/smarter-project-repositories/scripts/repos-status.sh [repository ...]
#
# The repositories default to those of smarter.apps.mcpserver.repositories, except smarter itself.
# The checkouts default to the parent of this repository; set SMARTER_PROJECT_DIR to use another.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
PROJECT_DIR="${SMARTER_PROJECT_DIR:-$(dirname "$ROOT")}"
REPOSITORIES=("$@")
if [ ${#REPOSITORIES[@]} -eq 0 ]; then
  REPOSITORIES=(smarter-cli smarter-python smarter-nodejs smarter-golang smarter-vscode-yaml
    smarter-deploy smarter-infrastructure)
fi

printf "%-24s %-12s %-8s %-11s %s\n" REPOSITORY BRANCH CHANGES COMMITTED REMOTE
for repository in "${REPOSITORIES[@]}"; do
  dir="$PROJECT_DIR/$repository"

  if ! git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
    printf "%-24s %s\n" "$repository" "no checkout at $dir"
    continue
  fi
  branch="$(git -C "$dir" branch --show-current)"
  changes="$(git -C "$dir" status --porcelain | wc -l | tr -d ' ')"
  local_sha="$(git -C "$dir" rev-parse HEAD)"
  committed="$(git -C "$dir" log -1 --format=%cs)"
  remote_sha="$(git -C "$dir" ls-remote origin "refs/heads/$branch" 2>/dev/null | cut -f1)"
  if [ -z "$remote_sha" ]; then
    remote="unknown (no origin/$branch, or offline)"
  elif [ "$remote_sha" = "$local_sha" ]; then
    remote="current"
  elif git -C "$dir" merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then
    remote="ahead of origin/$branch"
  else
    remote="behind or diverged from origin/$branch (${remote_sha:0:9})"
  fi
  printf "%-24s %-12s %-8s %-11s %s\n" "$repository" "$branch" "$changes" "$committed" "$remote"
done
