---
name: smarter-docker-environment
description: Use whenever Smarter code must run in its Docker containers (smarter-app, smarter-worker, smarter-worker-infrastructure, smarter-beat), for tests, migrations, manage.py commands or the dev server. Explains how to sync host edits into containers that have no bind mount, the docker cp traps, restarts, and the safety rules for the live credentials inside.
---

# Smarter Docker Environment

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

## The containers don't see your edits

There's **no bind mount** of the source. Edits on the host do nothing until you
copy them in. The containers can drift far behind the host, by dozens of files
and unapplied migrations. Before trusting any test result:

1. Compare md5s of the host files with the container's.
2. Copy the files that differ into **every** app container. Celery tasks run in
   the workers, so a stale worker runs stale task code even when smarter-app is
   current.
3. Fix ownership, restart, and wait for the dev server to come back.
4. Run `migrate` if the change includes migrations.

[scripts/sync-to-containers.sh](scripts/sync-to-containers.sh) does steps 1–3
for one or more subpaths:

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

- An unquoted `$FILES` is **not** word-split in zsh. Loop with
  `while read -r f; do ...; done <<< "$FILES"`, or pipe to `xargs`.
- Use absolute paths, or paths from the repository root. A wrong relative `cd`
  silently runs a command against the wrong tree.

## Safety: live credentials inside

The containers' kubeconfig points at the **real EKS cluster**, and their AWS
credentials can change real Route53 zones, ACM certificates, and node groups.
Anything you run there, including tests, can create real, billable
infrastructure. See `smarter-infrastructure-safety` before running anything that
deploys, verifies a domain, or scales a cluster.
