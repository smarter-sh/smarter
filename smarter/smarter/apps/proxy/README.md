# Proxy

Passthrough access to 3rd party LLM provider APIs, with API keys that Smarter
keeps as Secrets.

A Proxy forwards requests, as they are, to a provider's native API, e.g.
`https://api.openai.com/v1/`. Callers use the provider's own SDK, with the
Proxy's URL as its base URL and a Smarter API key in place of the provider's.
Smarter adds the provider's API key, from a Secret, so it never leaves Smarter.

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://<smarter>/api/v1/proxy/openai/",
    api_key="<Smarter API key>",
)
client.chat.completions.create(
    model="gpt-6-luna",
    messages=[{"role": "user", "content": "Hi"}],
)
```

Key features:

- passthrough of any method, path, query string, body and headers, including
  streams
- the provider's API key is a Smarter Secret. The caller's Smarter API key is
  never forwarded
- Smarter API keys in any SDK's header: `Authorization: Bearer`, `x-api-key`
  (Anthropic), `x-goog-api-key` (Gemini) or `api-key` (Azure OpenAI)
- `allowedPaths`, to limit callers to e.g. the inference endpoints
- budget controls: a budget's resource lock refuses requests with 402
- token usage is read from responses, including streams, and charged to the
  Proxy, the caller and the caller's account
- built-in Proxies for the built-in Providers, which every account may use

## Layout

- `models.py`: the `Proxy` Django ORM model
- `manifest/`: the Proxy manifest's Pydantic models, and its CLI broker
- `services.py`: the passthrough, `resolve_proxy()` and `ProxyForwarder`
- `authentication.py`: callers' Smarter API keys, in any SDK's header
- `api/v1/`: the passthrough endpoint, `/api/v1/proxy/<name>/<path>`
- `views/`, `urls.py`: the web console's list and manifest pages, at `/proxy/`
- `builtins.py`, `data/proxy/`: the built-in Proxy manifests, which
  `manage.py add_builtin_proxies` applies

See the documentation: `docs/source/smarter-resources/smarter-proxy.rst`.

## Tests

```console
python manage.py test smarter.apps.proxy.tests
```

The tests never call a real provider: `ProxyTestBase` installs a fake provider
with `configure_transport()`, and the passthrough refuses to call a real one
from the unit tests.
