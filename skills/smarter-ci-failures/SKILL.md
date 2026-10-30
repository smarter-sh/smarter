---
name: smarter-ci-failures
description: Use when the user gives a GitHub Actions run or job url (github.com/smarter-sh/<repo>/actions/runs/<id>, optionally /job/<id>) or says a workflow run, test run, shard, CI check or pull request check failed, e.g. "python shard 4 of 8 failed", "the test run failed but I can't download the logs". Covers downloading the failed jobs' logs with the bundled script (which works around GitHub's 502s, the "terminal escape sequences" refusal, and a missing gh login), reading the failures out of them, the Tests workflow's jobs and shards, reproducing a failure in the smarter-app container, deciding whether it is new or pre-existing, fixing it, and reporting.
---

# Investigating a Failed GitHub Actions Run

The user can't always read a run's logs: GitHub's log download often fails in the browser, and a log is
over 100,000 lines. Give them the cause, not the log.

## 1. Download and extract the failures

```console
skills/smarter-ci-failures/scripts/fetch-run-logs.sh <run url | job url | run id> [output dir]
```

Use your scratchpad as the output dir. The script prints:

- the run's workflow, event, branch, commit and its message, so you know **which code was tested**;
- every job and its conclusion;
- for each failed job (or only the job of a job url), its failures: each Python unittest `FAIL`/`ERROR`
  block with its traceback, the `Ran N tests` / `FAILED (...)` summary, Vitest's `×` lines and errors,
  and the `##[error]` lines of the step that failed;
- the paths of `<job id>.log` (the whole log, colors stripped, timestamps cut) and `<job id>.failures.txt`.

It handles what goes wrong when you do this by hand:

- **No gh login.** It reads `GH_TOKEN` or `GITHUB_TOKEN` from the repository's `.env`, without printing
  it. Never ask the user to `gh auth login`.
- **GitHub's api answers 502 or 503** (`failed to get jobs: HTTP 502`): every call is retried. A 502 is
  also why the user's own download failed: say so.
- **`gh run view --log-failed` and `gh api .../logs` refuse to print a log with color codes** ("the
  response contains terminal escape sequences"): it passes `--allow-escape-sequences` and strips them.

When the failures file is empty, read the end of the log, and search it for the step's `##[error]`.
A unittest failure printed by a shard is its own block at the end of its log; the `Traceback` lines
earlier in a log are usually logged errors of tests that passed (e.g. a broker's journaled error
response), not failures.

## 2. Know what failed

The **Tests** workflow (`.github/workflows/test.yml`, on pull requests to `main`) has these jobs:

| Job                     | What its failure means                                                         |
| ----------------------- | ------------------------------------------------------------------------------ |
| `fingerprint`           | The cache key step. Rare; read its log.                                        |
| `react`                 | `make react-test` and lint of `smarter/react`. Vitest failures.                |
| `python (shard N of 8)` | One eighth of the Django test suite, built from scratch in its own containers. |
| `python-report`         | Fails whenever any shard failed. Never the cause: find the shard that failed.  |

A shard's failure is either a test failure (`FAILED (failures=…, errors=…)`), or the platform failing
to start before the tests ran (no `Ran N tests` line: read the shard's setup steps, e.g. migrations,
`initialize_platform`). The other workflows (build, deploy, publish) are described in `build.yml`.

## 3. Is it new?

Compare the run's commit with the working tree: `git log --oneline -5` and `git show --stat <sha>`.

- A failure in code that a later commit, or the working tree, already changed may be fixed already: run
  the test on the current code before changing anything.
- A test that fails on a commit that didn't touch it is often a stale expectation left by an earlier
  commit, e.g. a response that gained a field. `git log -S'<field>'` finds the commit that added it.
- A test that passes locally and failed once in CI may be flaky (timing, ordering across shards, a live
  LLM call). Say so, with the evidence, rather than "fixing" a test that isn't broken.

## 4. Reproduce, fix, verify

Run the failed test by its dotted name in the smarter-app container (see `smarter-docker-environment` and
`smarter-python-testing`), after syncing your edits:

```console
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py test smarter.lib.drf.tests.test_listview_api"
```

Then run its whole package, and the pre-commit hooks on the files you changed. React failures:
`npx vitest run --project <package>` in `smarter/react`.

## 5. Report

Lead with the cause in one sentence: which job, which test, why it failed, and whether it is new or
pre-existing. Then the fix and how you verified it. Don't paste the log; the failures file's path is
enough. Never push or re-run the workflow: give the user the commit command (`smarter-git-commits`),
and say that the next push re-runs the checks.
