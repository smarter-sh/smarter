---
name: smarter-docker-environment
description: Use whenever Smarter code must run in its Docker containers (smarter-app, smarter-worker, smarter-worker-infrastructure, smarter-beat), for tests, migrations, manage.py commands or the dev server. Explains how to sync host edits into containers that have no bind mount, the docker cp traps, restarts, and the safety rules for the live credentials inside.
---

# Smarter Docker Environment

> **Read first: the host shell is zsh, and zsh does not word-split.** > `FILES=$(git diff --name-only); for f in $FILES; do docker cp "$f" ...; done`
> runs **once**, with every path joined into one "file name". `docker cp` fails,
> silently if its stderr is discarded, the containers keep the old code, and the
> tests "fail again for no reason". Agents have rediscovered this in session after
> session. Don't hand-write the loop: run
> [scripts/sync-changed-files.sh](scripts/sync-changed-files.sh), which copies
> exactly the files git lists as changed or new. If you must loop, use
> `while read -r f; do ...; done < file` or `xargs`, and never discard
> `docker cp`'s errors.

## The containers

| Container                          | Role                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------- |
| `smarter-app`                      | Django dev server on http://localhost:9357, and where tests and `manage.py` run |
| `smarter-worker`                   | Celery worker for operational tasks                                             |
| `smarter-worker-infrastructure`    | Celery worker for infrastructure tasks (deploys, DNS, certificates)             |
| `smarter-beat`                     | Celery beat scheduler                                                           |
| `smarter-mariadb`, `smarter-redis` | Database and cache/broker                                                       |

Host path `smarter/smarter/<path>` is `/home/smarter_user/smarter/smarter/<path>`
in every app container. The working directory for `manage.py` is
`/home/smarter_user/smarter`.

```console
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py <command>"
```

### Local hostnames

Two api domains are both valid locally, for different setups. Neither is a
misconfiguration:

- `api.localhost:9357` is `smarter_settings.environment_api_domain` for the
  bare local dev server.
- `api.local.smarter.sh` is the proxy host of a local Kubernetes deployment.
  `LLMClient.default_host` builds deployed LLMClient hosts on it, e.g.
  `stackademy-sql.3141-5926-5359.api.local.smarter.sh`.

The local dev server can't resolve a deployed LLMClient's own host in either
form, because `LLMClientHelper(request).llmclient` is `None`. So you can't
exercise a deployed host end to end with `HTTP_HOST`. Test those views with
`get_cached_llmclient_by_request` patched (see `smarter-python-testing`), and
never deploy an LLMClient for real to try (see `smarter-infrastructure-safety`).

## The containers don't see your edits

There's **no bind mount** of the source. Edits on the host do nothing until they
reach the containers, which can drift far behind the host, by dozens of files
and unapplied migrations. Celery tasks run in the workers, so a stale worker runs
stale task code even when smarter-app is current.

> **`make run` never returns.** It is `docker compose up`, attached to the
> containers' logs. Run in a foreground Bash call, it blocks the agent until the
> timeout or until someone stops the containers, and the user sees an agent
> that is stuck. Always start `make run` (and `make build && make run`) with
> `run_in_background: true`, then poll for the dev server as shown below. Never
> give it a long foreground timeout instead: that is the same mistake.

**Prefer a rebuild.** `make build && make run` rebuilds the images from the
host's tree and restarts every container, in about 5 seconds when only source
files changed. That beats copying files one at a time, and leaves no container
behind. `make run` is `docker compose up`, which stays in the foreground, so
start it in the background (with `run_in_background`, never `&` in a foreground
shell), then wait for the dev server and apply any migrations:

```console
make build && make run          # in the background
until [ "$(curl -s -o /dev/null -w '%{http_code}' localhost:9357/)" = "302" ]; do sleep 2; done
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py migrate"
```

`make build` doesn't collect static files. After a React change, use
`make react-build` instead (see `smarter-django-react`). It is safe to run
without asking: its build output isn't tracked, and it changes no
infrastructure.

**When a rebuild isn't possible**, e.g. while the user is running the stack
themselves, [scripts/sync-changed-files.sh](scripts/sync-changed-files.sh)
copies the files that git lists as changed or new into every app container,
fixes their ownership, restarts smarter-app, and waits for the dev server. It
takes seconds.

```console
skills/smarter-docker-environment/scripts/sync-changed-files.sh
```

[scripts/sync-to-containers.sh](scripts/sync-to-containers.sh) instead compares
every file's md5, which also catches containers that drifted from the host's
committed files, but takes many minutes over all of `smarter/smarter` (long
enough to look hung). Give it subpaths, and run it in the background:

```console
skills/smarter-docker-environment/scripts/sync-to-containers.sh apps/llmclient lib/unittest
```

## docker cp traps

- **Copying a directory into an existing directory nests it.**
  `docker cp apps/foo smarter-app:/.../apps/foo` creates `.../apps/foo/foo`.
  Copy files individually, or remove the target first, but see the next point.
- **Never `rm -rf` a directory in a container without diffing first.** Files
  created inside the container (by migrations, earlier sessions, or
  `makemigrations`) may not exist on the host, and they'd be lost. Copy anything
  container-only out first.
- **Copied files are root-owned**, so `smarter_user` can't modify or delete them,
  and `makemigrations` fails. Run
  `docker exec -u root <container> chown -R smarter_user <path>` afterwards.
- **Several copies in a row can kill the dev server.** Its auto-reloader is
  interrupted mid-restart. Tests that `apply_manifest()` over HTTP then fail with
  `httpx.ConnectError: Connection refused`. After syncing, run
  `docker restart smarter-app` and wait until `curl localhost:9357/` returns 302.

## Copying files out

Generated files (migrations, `coverage.xml`) are written in the container.
Copy them back to the host so they become part of the change:

```console
docker cp smarter-app:/home/smarter_user/smarter/smarter/apps/widget/migrations/0001_initial.py smarter/smarter/apps/widget/migrations/
```

## Shell notes (zsh on the host)

- Never name a variable `path` in zsh: it is tied to `$PATH`, and assigning it
  breaks every command that follows ("command not found: curl").
- An unquoted `$FILES` is **not** word-split in zsh (see the top of this page).
  Loop with `while read -r f; do ...; done <<< "$FILES"`, or pipe to `xargs`.
- Use absolute paths, or paths from the repository root. A wrong relative `cd`
  silently runs a command against the wrong tree.

## Testing a credential-free `make init`

To see what a newcomer gets from `make init` (no AWS, no api keys, no SMTP),
without touching the dev database, the workers or live infrastructure, run the
image on an isolated network:

1. `docker network create smarter-newcomer`, then throwaway `mariadb:latest` and
   `redis:latest` (`--requirepass smarter`) on it, with
   `--network-alias smarter-mariadb` and `--network-alias smarter-redis`. The
   hostnames are hard-coded in `settings/base.py`, so the aliases redirect
   everything.
2. Load `scripts/smarter_test_db.sql`, and grant `smarter` all privileges, as
   `docker-init` does.
3. Run `smarter:latest` with `--env-file` (a copy of the template, plus a Fernet
   key), and a copy of the host's `smarter/smarter` mounted over
   `/home/smarter_user/smarter/smarter`. The image has an empty kubeconfig and no
   `~/.aws`, so it holds no credentials.
4. Run each `docker-init` step separately (`reset_cache`, `migrate`,
   `initialize_platform`), recording each exit
   code, with two Celery workers (default and infrastructure queues) on the same
   network.
5. The logs are huge with `DEBUG_MODE=true`: strip the ANSI codes, and grep for
   `ERROR`, `Traceback` and the exit codes.

## Safety: live credentials inside

The containers' kubeconfig points at the **real EKS cluster**, and their AWS
credentials can change real Route53 zones, ACM certificates, and node groups.
Anything you run there, including tests, can create real, billable
infrastructure. See `smarter-infrastructure-safety` before running anything that
deploys, verifies a domain, or scales a cluster.
