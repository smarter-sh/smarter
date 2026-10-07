---
name: smarter-api-testing
description: Use when you need to exercise the Smarter REST API by hand (apply, get, describe, delete, deploy a manifest) against the local dev server, e.g. to reproduce a bug or confirm a fix end to end. Explains why to POST directly to /api/v1/cli/<command>/ with a throwaway API key instead of using the smarter CLI, and how to create and clean up that key.
---

# Smarter API Testing over HTTP

## Use HTTP, not the smarter CLI

To probe API behavior, POST straight to the local dev server at
`http://localhost:9357/api/v1/cli/<command>/`. **Don't run the `smarter` CLI**,
and don't depend on `~/.smarter/config.yaml`:

- The CLI is a separate program, so it adds a failure point of its own between
  you and the behavior you're testing.
- Its `local` API key goes stale whenever the dev database is rebuilt.

## Endpoints

| Command                       | Request                                                                                                                     |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| apply                         | `POST /api/v1/cli/apply/`, with the raw manifest YAML as the body                                                           |
| validate                      | `POST /api/v1/cli/validate/`, with the raw manifest YAML as the body                                                        |
| get                           | `POST /api/v1/cli/get/<Kind>/`                                                                                              |
| describe                      | `POST /api/v1/cli/describe/<Kind>/?name=<name>`                                                                             |
| delete                        | `POST /api/v1/cli/delete/<Kind>/?name=<name>`                                                                               |
| deploy / undeploy             | `POST /api/v1/cli/deploy/<Kind>/?name=<name>`. ⚠ **This creates real infrastructure.** See `smarter-infrastructure-safety` |
| logs                          | `POST /api/v1/cli/logs/<Kind>/?name=<name>`                                                                                 |
| example manifest, JSON schema | `POST /api/v1/cli/example-manifest/<Kind>/`, `/api/v1/cli/json-schema/<Kind>/`                                              |

`<Kind>` is the manifest kind exactly as it appears in YAML, for example
`CustomDomain` or `Guardrail`. Routes: `smarter/smarter/apps/api/v1/cli/urls.py`.

Every request carries `Authorization: Token <key>`. Responses are journaled
JSON: `{"data": {...}, ...}` on success, and an error with a matching HTTP status
on failure.

## 1. Create a throwaway key

Create your own key, owned by the user whose resources you're testing, and mark
it for deletion:

```console
docker exec smarter-app bash -c 'cd /home/smarter_user/smarter && python manage.py shell -c "
from smarter.lib.drf.models import SmarterAuthToken
from smarter.apps.account.utils import smarter_cached_objects as s
from smarter.apps.account.models import UserProfile
u = s.smarter_admin
up = UserProfile.objects.filter(user=u).first()
_, key = SmarterAuthToken.objects.create(user=u, user_profile=up, name=\"api_test_probe\", description=\"DELETE ME\", is_active=True)
print(\"KEY=\" + key)
"' 2>/dev/null | grep '^KEY='
```

The key is shown only once. Keep it in a shell variable or a scratch file, never
in the repository.

## 2. Call the API

```console
curl -s -X POST -H "Authorization: Token $KEY" http://localhost:9357/api/v1/cli/get/CustomDomain/
curl -s -X POST -H "Authorization: Token $KEY" "http://localhost:9357/api/v1/cli/describe/CustomDomain/?name=example_com"
curl -s -X POST -H "Authorization: Token $KEY" --data-binary @smarter/smarter/apps/llmclient/data/custom-domains/example-com.yaml \
  http://localhost:9357/api/v1/cli/apply/
```

Use `--data-binary` (not `-d`) for manifests, so the YAML's newlines survive.

Make sure smarter-app is running your current code first (see
`smarter-docker-environment`).

## 3. Delete the key

```console
docker exec smarter-app bash -c 'cd /home/smarter_user/smarter && python manage.py shell -c "
from smarter.lib.drf.models import SmarterAuthToken
print(SmarterAuthToken.objects.filter(name=\"api_test_probe\", description=\"DELETE ME\").delete())
"' 2>/dev/null
```

Also delete any resources you applied while probing, unless the user wants to
keep them.

## When to write a test instead

A manual probe confirms a behavior once. When a probe finds a bug, turn it into
a unit test (a broker test or a CLI view test in
`smarter/smarter/apps/api/v1/cli/tests/`) before fixing it. See
`smarter-python-testing`.
