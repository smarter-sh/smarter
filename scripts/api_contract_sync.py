#!/usr/bin/env python3
"""Check that a repository's copy of the Smarter api contract is current, and propose the sync where it isn't.

This is the core of ``.github/workflows/apiContractSync.yml``, the weekly API Contract Sync
workflow. The platform publishes its api as files that clients generate code from: the OpenAPI
document, a JSON Schema and an example manifest of every SAM kind
(``smarter/smarter/apps/api/v1/contract/``), and the chat and journal contracts. Five other
repositories of the smarter-sh organization keep a pinned copy of those files, and test their own
code against it (see the ``smarter-project-repositories`` skill):

- ``smarter-python``, ``smarter-nodejs`` and ``smarter-golang``, the SDKs, which also generate
  their SAM models from the schemas,
- ``smarter-cli``, whose contract test checks each command against the OpenAPI document,
- ``smarter-vscode-yaml``, the VS Code extension, which bundles the schemas and examples.

A copy goes stale whenever a platform release changes the contract, and nothing tells the
repository. This script, run once per repository by the workflow, finds out, and opens the
pull request that brings the copy up to date.

Usage, from the root of the repository's checkout::

    python3 -I scripts/api_contract_sync.py status --repository smarter-sh/smarter-python \\
        --tag v0.40.4 --sha <full sha> --shipped smarter/models/sam \\
        --baseline success --tests failure --output result.json
    python3 -I scripts/api_contract_sync.py publish --result result.json --base alpha \\
        --run-url URL [--dry-run]
    python3 -I scripts/api_contract_sync.py report --results DIR --tag v0.40.4 --run-url URL \\
        --summary "$GITHUB_STEP_SUMMARY" | python3 -I scripts/slack_post.py --channel general

Before ``status`` runs, the workflow has already, in the repository's checkout:

1. run its unit tests with its current copy (the *baseline*),
2. run its own ``scripts/sync-contracts.sh`` at the platform's latest release tag, and regenerated
   the code that it generates from the contract, as its ``make sam-models`` (or ``make
   contracts``) does,
3. run its unit tests again, with the synced copy.

Then the three commands do this:

- ``status`` reads the checkout's ``git status``. Any file that the sync or the regeneration
  changed means the repository's copy was out of date. It writes a :class:`Result` as JSON.
- ``publish`` acts on one result, with ``gh`` and ``git``, authorized by ``GH_TOKEN``. An
  out-of-date repository gets one open issue, labeled :data:`LABEL`, and one pull request from the
  branch :data:`BRANCH` into ``--base``, with the sync as a single commit. A pull request whose
  tests fail after the sync is a draft: the contract changed in a way that needs work in the SDK,
  which a maintainer pushes to the same branch. A later run updates the same issue and pull
  request, rather than opening more, and a repository that is current again has both closed.
- ``report`` reads every repository's result, appends one Markdown table to the run's page, and
  prints one Slack message: the repositories that need attention, or a clean bill of health when
  every one is current. It exits with 1 when a repository's tests fail, or publishing failed, so
  that the run is red.

It uses only Python's standard library, because the workflow's runner has no virtual environment:

- ``argparse`` reads the command line, with one subcommand per step.
- ``subprocess`` runs ``git`` and ``gh`` with an argument list, never through a shell, so that no
  argument is ever interpreted as shell syntax. Every call goes through :func:`run`, which the
  tests replace with a fake.
- ``dataclasses.dataclass`` writes :class:`Result`'s ``__init__`` from its annotated fields, and
  ``asdict()`` turns it into the JSON that the workflow passes between its jobs.
- ``json``, ``os``, ``pathlib`` and ``sys`` read and write the result files, the environment and the
  exit code.
"""

import argparse
import json
import os
import subprocess  # nosec B404: runs git and gh with fixed arguments
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

LABEL = "api-contract"
"""The label of the issue that this workflow opens in each repository.

It is how a later run finds the issue again, so a repository has at most one open issue with it.
"""

LABEL_COLOR = "1d76db"
"""The label's color, as GitHub takes it: six hex digits, without ``#``."""

LABEL_DESCRIPTION = "The copy of the Smarter platform's api contract is out of date"
"""The label's description, shown in the repository's list of labels."""

BRANCH = "api-contract-sync"
"""The branch of each repository that holds the sync commit.

It belongs to this workflow: every run rebuilds it from ``--base`` and force-pushes it, so that the
pull request always holds exactly one commit, the newest sync. A maintainer who pushes fixes to it
merges them before the next run, or moves them to a branch of their own.
"""

BOT_NAME = "github-actions[bot]"
"""The author of the sync commit."""

BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
"""The sync commit author's email: GitHub's own address for the Actions bot, which links its avatar."""

PLATFORM_URL = "https://github.com/smarter-sh/smarter"
"""The platform's repository, to which the issues and pull requests link the release tag."""

MAX_FILES = 40
"""The most changed files listed in an issue or pull request.

The rest are counted. A sync that adds a SAM kind changes a few files; one that renames a shared
model can change every kind's schema and generated module, which would bury the text around them.
"""

IGNORED_NAMES = ("SOURCE",)
"""File names that record where a copy came from, rather than any part of the contract.

``smarter-cli`` writes the platform version it copied into ``testdata/contracts/SOURCE``, so that
file changes on every release, even one that leaves the OpenAPI document as it was. A change to it
alone is not a reason to open a pull request. When the sync changes anything else, it is committed
with the rest.
"""

VERDICT_TEXT = {
    "current": ("current", ":white_check_mark:"),
    "outdated": ("out of date, compatible", ":arrows_counterclockwise:"),
    "broken": ("out of date, tests fail after the sync", ":x:"),
    "failing": ("tests fail before the sync", ":warning:"),
}
"""Each :attr:`Result.verdict`'s words, for the run's page and Slack, and its Slack emoji."""


@dataclass
class Result:  # pylint: disable=too-many-instance-attributes
    """
    One repository's check: what the sync changed in it, and whether its tests pass.

    ``status`` builds it from the checkout, and saves it as JSON in the runner's temporary folder.
    ``publish`` loads it, adds the urls of the issue and pull request that it opened or updated,
    and saves it again. The workflow then uploads it as an artifact, so that the ``report`` job,
    which runs on another runner, can read every repository's result.

    **Verdicts** (:attr:`verdict`):

    - ``current``: the sync changed nothing, and the tests pass. Nothing to do.
    - ``outdated``: the sync changed the copy, and the tests pass with it. The update is
      compatible, and its pull request is ready to merge.
    - ``broken``: the tests pass with the current copy and fail with the synced one, so the release
      changed the contract in a way that needs work in the repository. Its pull request is a draft.
    - ``failing``: the tests already fail with the current copy, so this check can't tell what
      the sync would break.
    """

    #: The repository, as ``owner/name``, e.g. ``smarter-sh/smarter-python``.
    repository: str
    #: The platform's release tag that the copy was synced with, e.g. ``v0.40.4``.
    tag: str
    #: The tag's full commit sha. The sync commit ends with it, for ``monthly-maintenance``.
    sha: str
    #: Every file that the sync and the regeneration changed, added or removed, sorted.
    changed: list[str] = field(default_factory=list)
    #: The paths (files or folders) whose contents the repository ships to its users, e.g. the
    #: Python SDK's generated ``smarter/models/sam``. A change to one is a ``fix``, which releases.
    shipped: list[str] = field(default_factory=list)
    #: The outcome of the tests with the current copy, as GitHub reports a step's: ``success``,
    #: ``failure``, ``cancelled`` or ``skipped``.
    baseline: str = "success"
    #: The outcome of the tests with the synced copy.
    tests: str = "success"
    #: The url of the issue that ``publish`` opened or updated, or empty.
    issue_url: str = ""
    #: The url of the pull request that ``publish`` opened or updated, or empty.
    pull_request_url: str = ""
    #: Why ``publish`` failed, e.g. ``publishing failed: HTTP 403``, or empty.
    error: str = ""

    @property
    def out_of_sync(self) -> bool:
        """
        Whether the repository's copy differs from the platform's.

        :returns: True when the sync changed any file other than a provenance record named in
            :data:`IGNORED_NAMES`.
        """
        return any(Path(path).name not in IGNORED_NAMES for path in self.changed)

    @property
    def broken(self) -> bool:
        """
        Whether the sync breaks the repository's tests.

        Only a baseline that passed can tell: when the tests already fail with the current copy,
        a failure after the sync says nothing about the contract.

        :returns: True when the tests pass with the current copy, and fail with the synced one.
        """
        return self.baseline == "success" and self.tests != "success"

    @property
    def ships_changes(self) -> bool:
        """
        Whether the sync changes anything that the repository ships to its users.

        It decides the sync commit's conventional-commit type (:func:`commit_subject`). The
        repositories release with semantic-release, which publishes a new version for a ``fix``
        and none for a ``chore``: a changed generated model is a change that users get, while a
        changed copy that only the tests read is not.

        :returns: True when a changed file is one of :attr:`shipped`, or inside one of its folders.
        """
        return any(
            path == prefix or path.startswith(prefix.rstrip("/") + "/")
            for path in self.changed
            for prefix in self.shipped
        )

    @property
    def verdict(self) -> str:
        """
        The result in one word, as the class's docstring defines them.

        :returns: ``current``, ``outdated``, ``broken`` or ``failing``.
        """
        if self.baseline != "success":
            return "failing"
        if self.broken:
            return "broken"
        return "outdated" if self.out_of_sync else "current"

    @classmethod
    def load(cls, path: str | Path) -> "Result":
        """
        Read a result that :meth:`save` wrote.

        Keys that the class doesn't know are ignored, so that an older script can read a newer
        result.

        :param path: The result's JSON file.
        :returns: The result.
        :raises OSError: When the file can't be read.
        :raises ValueError: When it isn't JSON.
        :raises TypeError: When it lacks a required field, e.g. ``repository``.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})

    def save(self, path: str | Path) -> None:
        """
        Write the result as indented JSON, replacing the file if it exists.

        :param path: The file to write.
        """
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


def run(*args: str, check: bool = True, input_text: str | None = None, strip: bool = True) -> str:
    """
    Run a command, without a shell, and return what it printed.

    Every ``git`` and ``gh`` call of this script goes through this function, so that the tests can
    replace it with a fake, and nothing in them reaches git or GitHub.

    :param args: The command and its arguments, e.g. ``("gh", "issue", "list", ...)``.
    :param check: Raise when the command fails. ``gh pr ready`` passes False, because it fails
        when the pull request already is in the state it asks for.
    :param input_text: Text to write to the command's standard input, e.g. an issue's body for
        ``--body-file -``. Long Markdown passes through stdin rather than as an argument.
    :param strip: Remove the output's leading and trailing white space, e.g. the newline after a
        url. ``git status --porcelain`` passes False, because its first line can start with a
        space that is part of the line's status, e.g. `` M``.
    :returns: The command's standard output.
    :raises subprocess.CalledProcessError: When ``check`` is True and the command exits with a
        status other than 0. Its ``stderr`` holds the command's error message.
    """
    completed = subprocess.run(  # nosec B603: fixed commands, arguments are never interpreted by a shell
        list(args), check=check, capture_output=True, text=True, input=input_text
    )
    return completed.stdout.strip() if strip else completed.stdout


def parse_porcelain(text: str) -> list[str]:
    """
    Read the paths out of ``git status --porcelain`` output.

    Each line of that format is a two-letter status, a space, and the path, e.g.
    `` M tests/data/contracts/openapi.json`` or ``?? tests/data/sam/New.schema.json``. A rename is
    ``R  old -> new``, of which the new path is kept. Git quotes a path that holds unusual
    characters, and the quotes are removed.

    :param text: The command's output.
    :returns: The paths, sorted, each once.
    """
    paths = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.strip('"'))
    return sorted(set(paths))


def changed_files() -> list[str]:
    """
    List the files that the sync and the regeneration changed in the current directory's checkout.

    The checkout was clean before the workflow synced it, so every change is the sync's. New
    files are listed one by one (``--untracked-files=all``), e.g. a new kind's schema and example,
    rather than as their folder.

    :returns: The changed, added and removed paths, relative to the repository's root.
    """
    return parse_porcelain(run("git", "status", "--porcelain", "--untracked-files=all", strip=False))


def file_list(paths: list[str]) -> str:
    """
    Write paths as a Markdown list, for an issue or a pull request.

    :param paths: The paths.
    :returns: One ``- `path``` line per path, cut to :data:`MAX_FILES` with a line that counts the
        rest, or ``- (none)`` when there are none.
    """
    lines = [f"- `{path}`" for path in paths[:MAX_FILES]]
    if len(paths) > MAX_FILES:
        lines.append(f"- ... and {len(paths) - MAX_FILES} more")
    return "\n".join(lines) or "- (none)"


def outcome(value: str) -> str:
    """
    Put a step's outcome, as GitHub reports it, in words for a table.

    :param value: ``success``, ``failure``, ``skipped`` or ``cancelled``.
    :returns: ``pass``, ``fail``, ``skipped`` or ``cancelled``, or ``value`` itself when it is
        none of those.
    """
    return {"success": "pass", "failure": "fail", "skipped": "skipped", "cancelled": "cancelled"}.get(value, value)


def tag_url(tag: str) -> str:
    """
    Link a platform release tag.

    :param tag: The tag, e.g. ``v0.40.4``.
    :returns: The url of the platform's tree at that tag.
    """
    return f"{PLATFORM_URL}/tree/{tag}"


def commit_subject(result: Result) -> str:
    """
    Write the sync commit's subject, which is also its pull request's title.

    It follows the ``smarter-contract-sync`` skill of the SDKs: ``fix(contracts)`` when the sync
    changes code that the repository ships (see :attr:`Result.ships_changes`), so that
    semantic-release publishes it, and ``chore(contracts)`` when only the test data changed.

    :param result: The repository's result.
    :returns: e.g. ``fix(contracts): sync with smarter v0.40.4``.
    """
    kind = "fix" if result.ships_changes else "chore"
    return f"{kind}(contracts): sync with smarter {result.tag}"


def commit_body(result: Result, run_url: str) -> str:
    """
    Write the sync commit's body.

    Its last line, ``Synced with smarter <full sha>``, is the one that the SDKs'
    ``monthly-maintenance`` skill reads (``smarter-delta.sh``) as the baseline of its next sync,
    so it must stay the last line, in that form.

    :param result: The repository's result.
    :param run_url: The workflow run's url, which the body cites.
    :returns: The body, in plain text.
    """
    return "\n".join(
        [
            f"Copy the Smarter platform's api contract at its release {result.tag} with "
            f"scripts/sync-contracts.sh, and regenerate the code generated from it.",
            "",
            f"Tests before the sync: {outcome(result.baseline)}. After it: {outcome(result.tests)}.",
            "",
            f"Opened by the platform's API Contract Sync workflow: {run_url}",
            "",
            f"Synced with smarter {result.sha}",
        ]
    )


def issue_title(result: Result) -> str:
    """
    Write the issue's title.

    :param result: The repository's result.
    :returns: A title that names the release, e.g. ``The api contract is out of date: sync with
        smarter v0.40.4``. A later run renames the issue to the newer release.
    """
    return f"The api contract is out of date: sync with smarter {result.tag}"


def issue_body(result: Result, run_url: str) -> str:
    """
    Write the issue's body: what changed, what the tests say, and what the maintainer does next.

    The advice depends on the verdict. A compatible sync only needs its pull request merged. A
    broken one needs work that the ``smarter-contract-sync`` skill's step 4 describes, e.g. a new
    operation to cover, or a recorded response that lacks a new required field. When the tests
    already fail before the sync, those come first.

    :param result: The repository's result.
    :param run_url: The workflow run's url, which the body links.
    :returns: The body, in GitHub Markdown.
    """
    if result.broken:
        status = (
            f"**The tests fail after the sync.** They pass with the current copy, so smarter {result.tag} changed the "
            "contract in a way that needs work here: a new operation, a removed or renamed field, or a recorded "
            "response that lacks a new required field. Follow the `smarter-contract-sync` skill, step 4."
        )
    elif result.baseline != "success":
        status = (
            "**The tests already fail before the sync**, so this check can't tell whether the new contract "
            "breaks anything. Fix the failing tests first."
        )
    else:
        status = "The tests pass after the sync, so the update is compatible. Review and merge the pull request."
    return "\n".join(
        [
            f"This repository's copy of the Smarter platform's api contract differs from the platform's latest "
            f"release, [smarter {result.tag}]({tag_url(result.tag)}).",
            "",
            status,
            "",
            "| Tests | Result |",
            "| --- | --- |",
            f"| Before the sync | {outcome(result.baseline)} |",
            f"| After the sync | {outcome(result.tests)} |",
            "",
            f"Files that `scripts/sync-contracts.sh {result.tag}` and the regeneration change:",
            "",
            file_list(result.changed),
            "",
            f"To sync by hand: `make sam-models SMARTER_REF={result.tag}` in the SDKs, "
            f"`make contracts SMARTER_REF={result.tag}` in the cli and the extension.",
            "",
            f"Found by the platform's weekly [API Contract Sync]({run_url}) workflow, which updates this issue "
            "and its pull request on every run, and closes both once the copy is current.",
        ]
    )


def pull_request_body(result: Result, run_url: str, issue_number: str) -> str:
    """
    Write the sync pull request's body.

    :param result: The repository's result.
    :param run_url: The workflow run's url, which the body links.
    :param issue_number: The number of the repository's open issue, which the body closes on merge
        (``Closes #<number>``), or empty for none.
    :returns: The body, in GitHub Markdown. For a broken sync, it says why the pull request is a
        draft, and where its fixes go.
    """
    lines = [
        f"Syncs this repository's copy of the Smarter platform's api contract with its release "
        f"[smarter {result.tag}]({tag_url(result.tag)}), and regenerates the code generated from it.",
        "",
    ]
    if issue_number:
        lines += [f"Closes #{issue_number}", ""]
    if result.broken:
        lines += [
            "**Draft: the tests fail after the sync.** Push the fixes they need to this branch "
            "(see the `smarter-contract-sync` skill, step 4), then mark it ready for review.",
            "",
        ]
    lines += [
        "| Tests | Result |",
        "| --- | --- |",
        f"| Before the sync | {outcome(result.baseline)} |",
        f"| After the sync | {outcome(result.tests)} |",
        "",
        "Changed files:",
        "",
        file_list(result.changed),
        "",
        f"Opened by the platform's weekly [API Contract Sync]({run_url}) workflow. A later run force-pushes "
        f"the branch `{BRANCH}` with the newest sync, so commit any fixes before the next run, or rename "
        "the branch.",
    ]
    return "\n".join(lines)


def find_open(kind: str, repository: str, *selector: str) -> dict | None:
    """
    Find the open issue or pull request that an earlier run opened.

    :param kind: ``issue`` or ``pr``, the ``gh`` command to list them with.
    :param repository: The repository, as ``owner/name``.
    :param selector: ``gh``'s filter, e.g. ``("--label", LABEL)`` for the issue, or
        ``("--head", BRANCH)`` for the pull request.
    :returns: The first match, as ``{"number": ..., "url": ...}``, or None when there is none.
    :raises subprocess.CalledProcessError: When ``gh`` fails, e.g. on a token that can't read the
        repository.
    """
    text = run(
        "gh", kind, "list", "--repo", repository, "--state", "open", *selector, "--json", "number,url", "--limit", "1"
    )  # fmt: skip
    items = json.loads(text or "[]")
    return items[0] if items else None


def close_stale(result: Result) -> None:
    """
    Close the issue and the pull request of an earlier run, now that the repository's copy is current.

    A maintainer may have synced by hand, or merged the pull request without the issue closing.
    Each is closed with a comment that says why. The pull request's branch, :data:`BRANCH`, is
    deleted with it.

    :param result: The repository's result, whose verdict is ``current``.
    :raises subprocess.CalledProcessError: When ``gh`` fails.
    """
    comment = f"The copy is current with smarter {result.tag}. Closed by the API Contract Sync workflow."
    pull_request = find_open("pr", result.repository, "--head", BRANCH)
    if pull_request:
        run(
            "gh", "pr", "close", str(pull_request["number"]), "--repo", result.repository,
            "--comment", comment, "--delete-branch",
        )  # fmt: skip
    issue = find_open("issue", result.repository, "--label", LABEL)
    if issue:
        run("gh", "issue", "close", str(issue["number"]), "--repo", result.repository, "--comment", comment)


def open_or_update_issue(result: Result, run_url: str) -> dict:
    """
    Open the repository's issue, or update the one that an earlier run opened.

    It first creates the label :data:`LABEL`, or updates it (``--force``), because ``gh issue
    create`` fails on a label that the repository doesn't have. An open issue with the label gets
    the new release's title and body, so that a repository never has more than one.

    :param result: The repository's result, whose copy is out of date.
    :param run_url: The workflow run's url, which the body links.
    :returns: The issue, as ``{"number": ..., "url": ...}``.
    :raises subprocess.CalledProcessError: When ``gh`` fails.
    """
    run(
        "gh", "label", "create", LABEL, "--repo", result.repository,
        "--color", LABEL_COLOR, "--description", LABEL_DESCRIPTION, "--force",
    )  # fmt: skip
    title, body = issue_title(result), issue_body(result, run_url)
    issue = find_open("issue", result.repository, "--label", LABEL)
    if issue:
        run(
            "gh", "issue", "edit", str(issue["number"]), "--repo", result.repository,
            "--title", title, "--body-file", "-", input_text=body,
        )  # fmt: skip
        return issue
    url = run(
        "gh", "issue", "create", "--repo", result.repository, "--title", title, "--label", LABEL,
        "--body-file", "-", input_text=body,
    )  # fmt: skip
    return {"number": url.rstrip("/").rsplit("/", 1)[-1], "url": url}


def push_sync_commit(result: Result, run_url: str) -> None:
    """
    Commit the sync on the branch :data:`BRANCH`, and force-push it.

    It runs in the workflow's checkout of the repository, at ``--base``, with every change of the
    sync in its working tree. The branch is rebuilt from there on every run, so a force-push is
    what keeps the pull request at one commit, the newest sync: the branch belongs to this
    workflow. ``actions/checkout`` left the token in the checkout's git configuration, which
    authorizes the push.

    :param result: The repository's result, whose copy is out of date.
    :param run_url: The workflow run's url, which the commit body cites.
    :raises subprocess.CalledProcessError: When ``git`` fails, e.g. on a token that can't push.
    """
    run("git", "config", "user.name", BOT_NAME)
    run("git", "config", "user.email", BOT_EMAIL)
    run("git", "checkout", "-B", BRANCH)
    run("git", "add", "--all")
    run(
        "git",
        "commit",
        "--quiet",
        "--file",
        "-",
        input_text=commit_subject(result) + "\n\n" + commit_body(result, run_url),
    )
    run("git", "push", "--force", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}")


def open_or_update_pull_request(result: Result, run_url: str, base: str, issue_number: str) -> str:
    """
    Open the repository's sync pull request, or update the one that an earlier run opened.

    A new pull request is a draft when the sync breaks the tests. An existing one gets the new
    release's title and body, and is moved into or out of draft, because the verdict can change
    from one run to the next: a maintainer's fix makes it ready, and a newer release can break it
    again. ``gh pr ready`` fails on a pull request that already is in the state it asks for, which
    is ignored.

    :param result: The repository's result, whose copy is out of date.
    :param run_url: The workflow run's url, which the body links.
    :param base: The branch that the pull request merges into, e.g. ``alpha``.
    :param issue_number: The repository's issue, which the pull request closes on merge.
    :returns: The pull request's url.
    :raises subprocess.CalledProcessError: When ``gh`` fails.
    """
    title, body = commit_subject(result), pull_request_body(result, run_url, issue_number)
    pull_request = find_open("pr", result.repository, "--head", BRANCH)
    if pull_request:
        number = str(pull_request["number"])
        run(
            "gh",
            "pr",
            "edit",
            number,
            "--repo",
            result.repository,
            "--title",
            title,
            "--body-file",
            "-",
            input_text=body,
        )
        draft_flag = [] if result.broken else ["--undo"]
        run("gh", "pr", "ready", number, "--repo", result.repository, *draft_flag, check=False)
        return pull_request["url"]
    draft = ["--draft"] if result.broken else []
    return run(
        "gh", "pr", "create", "--repo", result.repository, "--base", base, "--head", BRANCH,
        "--title", title, "--body-file", "-", *draft, input_text=body,
    )  # fmt: skip


def publish(result: Result, base: str, run_url: str, dry_run: bool) -> Result:
    """
    Open, update or close the repository's issue and pull request, as its result says.

    - A dry run, or a run without ``GH_TOKEN`` (the workflow's ``PAT`` secret), writes nothing.
    - A repository whose tests fail before the sync, and whose copy is current, has nothing to
      propose.
    - A current repository has the issue and pull request of an earlier run closed
      (:func:`close_stale`).
    - An out-of-date repository gets its issue (:func:`open_or_update_issue`), the sync commit on
      :data:`BRANCH` (:func:`push_sync_commit`), and its pull request
      (:func:`open_or_update_pull_request`), in that order, so that the pull request can close the
      issue.

    **Side effects:** writes issues, labels, a branch and a pull request to the repository on
    GitHub, and commits in the current directory's checkout.

    :param result: The repository's result. Its :attr:`Result.issue_url` and
        :attr:`Result.pull_request_url` are set when they are opened or updated.
    :param base: The branch that the pull request merges into, e.g. ``alpha``.
    :param run_url: The workflow run's url, which the texts link.
    :param dry_run: Report the verdict only.
    :returns: ``result``, updated.
    :raises subprocess.CalledProcessError: When ``git`` or ``gh`` fails.
    """
    if dry_run:
        print(f"{result.repository}: {result.verdict}. Dry run: nothing is written to GitHub.")
        return result
    if not os.environ.get("GH_TOKEN"):
        print(f"::warning::{result.repository}: no GH_TOKEN (the PAT secret), so nothing is written to GitHub.")
        return result
    if result.baseline != "success" and not result.out_of_sync:
        print(f"{result.repository}: its tests fail before the sync. Nothing to propose.")
        return result
    if not result.out_of_sync:
        close_stale(result)
        print(f"{result.repository}: current with smarter {result.tag}.")
        return result
    issue = open_or_update_issue(result, run_url)
    result.issue_url = issue["url"]
    push_sync_commit(result, run_url)
    result.pull_request_url = open_or_update_pull_request(result, run_url, base, str(issue["number"]))
    print(f"{result.repository}: {result.verdict}. Issue {result.issue_url}, pull request {result.pull_request_url}")
    return result


def summary_markdown(results: list[Result], tag: str, run_url: str) -> str:
    """
    Write the run's job summary: one table row per repository.

    GitHub shows it on the run's page, so that a maintainer sees every repository's verdict, test
    outcomes, and links without opening each job's log.

    :param results: Every repository's result.
    :param tag: The platform's release tag that the run checked against.
    :param run_url: The workflow run's url.
    :returns: The summary, in GitHub Markdown.
    """
    lines = [
        f"## API contract sync with smarter {tag}",
        "",
        "| Repository | Status | Tests before | Tests after | Changed files | Issue | Pull request |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        text, _ = VERDICT_TEXT[result.verdict]
        issue = f"[issue]({result.issue_url})" if result.issue_url else ""
        pull_request = f"[pull request]({result.pull_request_url})" if result.pull_request_url else ""
        error = f" ({result.error})" if result.error else ""
        lines.append(
            f"| {result.repository} | {text}{error} | {outcome(result.baseline)} | {outcome(result.tests)} "
            f"| {len(result.changed)} | {issue} | {pull_request} |"
        )
    if not results:
        lines.append("| (no results) | | | | | | |")
    lines += ["", f"[The run]({run_url})"]
    return "\n".join(lines) + "\n"


def slack_message(results: list[Result], tag: str, run_url: str) -> str:
    """
    Write the run's one Slack message, in Slack's mrkdwn.

    Every run posts exactly one message, to #general. When every repository is current, and
    publishing failed nowhere, it is a clean bill of health that names them. Otherwise it lists
    each repository that needs attention, with its verdict, any error, and links to its issue and
    pull request, then counts the current ones. No result at all means that every check job failed
    before it wrote one, which is reported too.

    :param results: Every repository's result.
    :param tag: The platform's release tag that the run checked against.
    :param run_url: The workflow run's url.
    :returns: The message. ``scripts/slack_post.py`` posts it.
    """
    healthy = bool(results) and all(result.verdict == "current" and not result.error for result in results)
    if healthy:
        names = ", ".join(result.repository.rsplit("/", 1)[-1] for result in results)
        return (
            f":white_check_mark: *API contract: clean bill of health.* Every repository's copy of the api contract "
            f"is current with smarter {tag}, and its tests pass: {names}. <{run_url}|The run>"
        )
    lines = [f"*API contract sync with smarter {tag}*"]
    current = [result for result in results if result.verdict == "current" and not result.error]
    for result in results:
        if result in current:
            continue
        text, emoji = VERDICT_TEXT[result.verdict]
        if result.error:
            text = f"{text}; {result.error}"
        links = [
            f"<{url}|{name}>"
            for name, url in (("issue", result.issue_url), ("pull request", result.pull_request_url))
            if url
        ]
        lines.append(f"{emoji} {result.repository}: {text}" + (f" ({', '.join(links)})" if links else ""))
    if current:
        names = ", ".join(result.repository.rsplit("/", 1)[-1] for result in current)
        lines.append(f":white_check_mark: {len(current)} more current: {names}")
    if not results:
        lines.append(":warning: No repository reported a result.")
    lines.append(f"<{run_url}|The run>")
    return "\n".join(lines)


def load_results(directory: str) -> list[Result]:
    """
    Read every repository's result that the check jobs uploaded.

    The ``report`` job downloads every artifact into one folder. A file that isn't a result, e.g.
    one cut short by a cancelled job, is skipped: the report covers the results it has, and
    :func:`main` fails when it has none.

    :param directory: The folder, searched recursively for ``*.json`` files.
    :returns: The results, sorted by repository.
    """
    results = []
    for path in sorted(Path(directory).rglob("*.json")):
        try:
            results.append(Result.load(path))
        except (OSError, ValueError, TypeError):
            continue
    return sorted(results, key=lambda result: result.repository)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Read the command line: one of the subcommands ``status``, ``publish`` and ``report``.

    :param argv: The arguments, without the program's name. None reads ``sys.argv``.
    :returns: The parsed arguments, with the subcommand's name in ``command``.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    status = commands.add_parser("status", help="Write the checkout's result as JSON.")
    status.add_argument("--repository", required=True, help="e.g. smarter-sh/smarter-python")
    status.add_argument("--tag", required=True, help="The platform's release tag, e.g. v0.40.4")
    status.add_argument("--sha", required=True, help="The tag's full commit sha.")
    status.add_argument("--shipped", default="", help="Space-separated paths that the repository ships to its users.")
    status.add_argument("--baseline", default="success", help="The tests' outcome before the sync.")
    status.add_argument("--tests", default="success", help="The tests' outcome after the sync.")
    status.add_argument("--output", required=True)

    publish_parser = commands.add_parser("publish", help="Open, update or close the issue and pull request.")
    publish_parser.add_argument("--result", required=True)
    publish_parser.add_argument("--base", default="alpha", help="The branch that the pull request merges into.")
    publish_parser.add_argument("--run-url", default="")
    publish_parser.add_argument("--dry-run", action="store_true")

    report = commands.add_parser("report", help="Summarize every repository's result.")
    report.add_argument("--results", required=True, help="A directory holding the result files.")
    report.add_argument("--tag", required=True)
    report.add_argument("--run-url", default="")
    report.add_argument("--summary", help="A file to append the Markdown summary to.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Run one subcommand.

    ``publish`` saves its result even when it fails, with the failure's last line in
    :attr:`Result.error`, so that the report says which repository it was, and what GitHub
    refused. ``gh`` and ``git`` never print the token.

    :param argv: The arguments, without the program's name. None reads ``sys.argv``.
    :returns: The exit code: 0, or 1 when ``publish`` failed, or when ``report`` found no result, a
        repository whose tests fail, or a failed publish.
    """
    args = parse_args(argv)
    if args.command == "status":
        result = Result(
            repository=args.repository,
            tag=args.tag,
            sha=args.sha,
            changed=changed_files(),
            shipped=args.shipped.split(),
            baseline=args.baseline,
            tests=args.tests,
        )
        result.save(args.output)
        print(f"{result.repository}: {result.verdict}, {len(result.changed)} changed files.")
        return 0
    if args.command == "publish":
        result = Result.load(args.result)
        try:
            publish(result, args.base, args.run_url, args.dry_run)
        except subprocess.CalledProcessError as error:
            last_line = ((error.stderr or "").strip().splitlines() or [str(error)])[-1]
            result.error = f"publishing failed: {last_line}"
            print(f"{result.repository}: {result.error}", file=sys.stderr)
            result.save(args.result)
            return 1
        result.save(args.result)
        return 0
    results = load_results(args.results)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as summary:
            summary.write(summary_markdown(results, args.tag, args.run_url))
    print(slack_message(results, args.tag, args.run_url))
    return 1 if not results or any(result.verdict in ("broken", "failing") or result.error for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
