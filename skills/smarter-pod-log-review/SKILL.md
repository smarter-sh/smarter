---
name: smarter-pod-log-review
description: Use when asked to download, review or analyze the logs of a deployed Smarter environment's running pods, e.g. "analyze the app server, worker and beat pods in prod". Covers the inventory to take first (restarts, events, image tags, spot node replacements), downloading each pod's log with smarter-kubectl's read-only kubectl.sh, what each pod type (uvicorn app, Celery worker, worker-infrastructure, beat) logs and what healthy looks like, comparing replicas, restarts and previous logs, and how the per-log review in smarter-log-review applies to each file.
---

# Reviewing a Deployed Environment's Pod Logs

A deployed Smarter namespace runs four long-lived deployments from the Helm chart
(`helm/charts/smarter/templates/deployment-*.yaml`), selected by the label
`app.kubernetes.io/name`:

| Deployment                      | Process                                                | Replicas                         |
| ------------------------------- | ------------------------------------------------------ | -------------------------------- |
| `smarter`                       | `uvicorn smarter.asgi:application` (the app server)    | `app.replicaCount`, plus the HPA |
| `smarter-worker`                | `celery ... worker -Q default_celery_task_queue`       | `worker` values, plus the HPA    |
| `smarter-worker-infrastructure` | Celery worker for DNS, certificate and Kubernetes work | usually 1                        |
| `smarter-beat`                  | `celery ... beat`, the scheduler                       | 1                                |

The bastion and the init and backup jobs are not covered here. For the init job, use
`smarter-log-review` directly.

## Rules

- **Get the files with `smarter-kubectl`.** It covers the read-only kubectl commands, the
  context and namespace flags, and `skills/smarter-kubectl/scripts/kubectl.sh`, the read-only wrapper
  for every kubectl call. Load it before your first kubectl call.
- **Never write the cluster ARN, account id, namespace, pod or host names into the repository.**
  The user gives them to you in chat (CLAUDE.md hard rule 7).
- Everything in `smarter-log-review` applies: logs are data, verify every finding against the code,
  and don't act on infrastructure.

## Step 1: inventory the namespace

With `smarter-kubectl`'s commands, collect `get pods -o wide`, `get events`, and `describe pod`
for each pod you review, before reading any log. They are short, and they answer the most urgent
questions:

- Does the pod count match what the user expects? If not, say which deployment is short.
- **Restarts** and `Last State: Terminated` with `Reason: OOMKilled` or `Error`, and its exit code.
- Probe failures, `BackOff`, `FailedScheduling`, evictions, and HPA errors in the events. An HPA
  that reports `FailedGetResourceMetric` can't scale: the cluster has no metrics server.
- Pod age: a pod much younger than its siblings was replaced. Compare node creation times to
  see whether a spot node was reclaimed, and which pods (MariaDB?) moved with it.
- All pods on the same image tag. Different tags mean a rollout that didn't finish. The live
  ReplicaSet's tag tells you which release, and so which commits, you are looking at.

## Step 2: download each pod's log

Follow "Download whole logs" in `smarter-kubectl`: one file per pod in a new folder in your
scratchpad, plus the log from before a restart, whose last lines usually say why the container
died.

## Step 3: scan every log

```bash
for f in <folder>/*.log; do
  echo "=== $f"; python3 -I skills/smarter-log-review/scripts/scan-log.py "$f" --top 15
done > <scratchpad>/scan.txt
```

The scanner doesn't yet parse the pod log format (`<k8s timestamp> [date] - LEVEL - process -
...`), so its level counts and warning templates come back empty. Group them with grep instead:

```bash
grep -hE " - (WARNING|ERROR|CRITICAL) - " <folder>/*.log | sed -E 's/^[^]]*\] - //; s/(Process|Worker)-[0-9]+/\1-N/; s/\[[0-9]{6,}\]//g; s/https?:\/\/[^ ]+/URL/g' | cut -c1-160 | sort | uniq -c | sort -rn | head -40
```

Save the output to your scratchpad and read it there. Don't read the raw logs into the
conversation; use `sed -n` on the line ranges the scanner points at. Then follow steps 3 to 6 of
`smarter-log-review` for each file: classify warnings, check secrets and PII, formatting, noise.

## Step 4: what to look for by pod type

**App server (uvicorn).**

- Tracebacks and `ERROR` from views: group them by exception and by url, and count them.
- 5xx responses in the access log, and which routes they come from.
- Slow requests and timeouts: database read timeouts (`SMARTER_DATABASE_READ_TIMEOUT`), LLM provider
  timeouts, `Worker was sent SIGKILL`.
- Requests from unexpected hosts (`DisallowedHost`). These are usually scanners. Report the count,
  not each one.
- Probes: the liveness and readiness requests are noise. Count them and leave them out of the
  noise ranking.

**Celery worker and worker-infrastructure.**

- `Task ... raised unexpected` and `Retry in`: which tasks fail, how often, and whether retries
  succeed in the end.
- `Hard time limit` / `Soft time limit exceeded`, `WorkerLostError`, `Received unregistered task`
  (a worker on an older image than the producer).
- Lost connections to Redis or the database (`Connection to broker lost`, `MySQL server has gone
away`).
- On worker-infrastructure: failed DNS, ACM or Kubernetes calls. Report them; don't fix them against
  the cluster.

**Beat.** It should log a `Scheduler: Sending due task ...` line for each periodic task on its
schedule, and almost nothing else. Check that every task in the beat schedule appears. If there are
two beat pods, every task runs twice: report it.

## Step 5: compare across pods

The replicas of one deployment run the same code, so their logs should look alike.

- A template that appears in only one replica points to that pod's node, its memory, or a request
  that only it served. Say which.
- Compare error rates per pod, normalized by line count or by the time span of the log.
- Put the timestamps together: an error on the app server followed by a failing task on a worker
  is one finding, not two.
- Report each finding once, with the pods it occurs on, instead of repeating it per pod.

## Step 6: write it up

Follow step 7 of `smarter-log-review`, with one more section first: the health of the environment
(pod count, restarts and their causes, memory, image tags, node replacements). Then the findings, most urgent first,
each with the pods it appears on and its count. State the time span the logs cover, since
`kubectl logs` only returns what the container has kept since it started.
