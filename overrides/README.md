# Overrides: local development only. NOT for prod, alpha, or any other environment on AWS

**Nothing in this directory reaches prod, alpha or any other AWS environment.** It is never built into the
Docker image, and no deployed pod reads it. For those environments, put your overrides in the Helm chart, as
`DJANGO_<SETTING>` variables in `env` in `helm/charts/smarter/values.yaml`, or in the values that your
deployment passes to `helm upgrade` (see "On Kubernetes" below).

This directory holds the Django overrides for **local development** (`make run`, Docker Compose), which
overwrite Smarter's Django settings.

> **An override is a hammer.** It replaces Smarter's value of that setting outright, however
> carefully that value was built: many of Smarter's settings are computed per environment (the database, the
> caches, storage, allowed hosts, CORS and CSRF origins, cookie security, the Content Security Policy), and
> nothing derived from the old value is computed again. A list or dictionary is replaced whole, not merged.
> Only the type is checked, never the meaning, so a wrong value can stop the platform or quietly weaken its
> security. Read how Smarter sets a setting in `smarter/smarter/settings/` before you override it, prefer a
> `SMARTER_*` setting where one exists, and change as few as you can.

## Locally

1. Copy `settings.example.yaml` to `settings.yaml` in this directory. Git ignores `settings.yaml`.
2. Write each setting as `NAME: value`, in YAML. `settings.example.yaml` has an example of each kind of value.
3. Restart the containers that read Django's settings:
   `docker compose restart smarter-api smarter-worker smarter-worker-infrastructure smarter-beat`.

Docker Compose mounts this directory read-only at `/home/smarter_user/overrides/` in those containers.
`smarter/smarter/settings/overrides.py` applies the file after all of Smarter's settings. A `DJANGO_<SETTING>`
environment variable, e.g. in `.env`, supersedes the file.

The test shards (`make docker-test`) don't mount this directory, so your overrides don't change the
tests. Tests that you run in the dev containers with `docker exec` do read it.

## `DJANGO_*` environment variables

The same code also reads every environment variable named `DJANGO_<SETTING>`, e.g.
`DJANGO_SESSION_COOKIE_AGE=3600`, and sets that Django setting. A variable supersedes the same setting in
`settings.yaml`, and all of Smarter's settings. They are the quickest way to change one setting:

- **Locally:** add the variable to `.env`, then recreate the containers (`make run`); Docker Compose reads
  `.env` when it creates them.
- **On Kubernetes:** add it to `env` in the Helm chart's values, e.g. `DJANGO_SESSION_COOKIE_AGE: "3600"`.

A variable's text is converted to the type of the setting's value: `true` for a boolean, `3600` for an
integer, `a,b` or a JSON list for a list. Nested settings are easier to write in the file.
`DJANGO_SETTINGS_MODULE` is Django's own, and isn't a setting.

## On Kubernetes (alpha, prod, and every other environment on AWS)

Write each setting as a `DJANGO_<SETTING>` variable in `env` in the Helm chart's values. Quote each value,
and write a list or a dictionary as JSON:

```yaml
env:
  DJANGO_SESSION_COOKIE_AGE: "3600"
  DJANGO_ADMINS: '["ops@example.com"]'
```

The chart mounts no settings file, and nothing in this directory reaches its pods.

The full explanation, with the order in which settings supersede each other, is in the docs: Configuration,
Overrides (`docs/source/smarter-platform/overrides.rst`).
