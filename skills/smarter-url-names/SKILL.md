---
name: smarter-url-names
description: Use when adding or changing a Django url pattern, a urls.py, or code that reverses a url in Smarter (reverse(), {% url %}, a model's *_url property, a context processor's links, a test's self.url()), e.g. a new console page, a new api route, a workbench tab. Covers the <App>ReverseNames class whose attributes are to_snake_case(<ViewClass>.__name__), the app's namespace in const.py, the two ways to call smarter.lib.django.shortcuts.reverse (variadic without kwargs, one joined string with kwargs), reversing against ROOT_URLCONF from a deployed LLMClient's host, absolute urls, the _by_id/_by_hashed_id suffixes, and the legacy shapes not to copy.
---

# Smarter Url Names

Every url name in Smarter is derived from the view class that serves it. A view named
`LLMClientDeploymentView` is reversed as `llm_client_deployment_view`, always, and nobody types that
string: it is computed once, in a class beside the url patterns, and every caller reads the class
attribute. Rename the view and every name follows; mistype the attribute and Python fails at import,
not a user at runtime.

The decision and its reasons are [ADR-032](../../docs/source/adr/032-url-names.rst). The newest, cleanest examples to copy: `apps/guardrail/urls.py`, `apps/llmclient/urls.py`,
`apps/prompt/urls.py` (console pages), and `apps/guardrail/api/v1/urls.py` (an api).

## The pattern

### 1. The namespace lives in the app's `const.py`

```python
# smarter/apps/guardrail/const.py
namespace = "guardrail"
```

`urls.py` sets `app_name = namespace`, and the parent urlconf includes it under the same constant:

```python
# smarter/urls/console.py
from smarter.apps.guardrail import urls as guardrail_urls
from smarter.apps.guardrail.const import namespace as guardrail_namespace

path("guardrail/", include(guardrail_urls, namespace=guardrail_namespace)),
```

A nested urls module (`dashboard/views/passthrough/urls.py`) does the same with its own `const.py`,
and the parent includes it with `namespace=<module>.app_name`.

### 2. One `<Prefix>ReverseNames` class per urls module

```python
from smarter.common.utils import to_snake_case

from .const import namespace
from .views.detailview import GuardrailDetailView
from .views.listview import GuardrailListView

app_name = namespace


class GuardrailReverseNames:
    """Reverse view names for the guardrail app."""

    namespace = namespace

    listview = to_snake_case(GuardrailListView.__name__)
    detailview = to_snake_case(GuardrailDetailView.__name__)
    listview_api_all = to_snake_case(GuardrailListApiView.__name__) + "_all"


urlpatterns = [
    path("", GuardrailListView.as_view(), name=GuardrailReverseNames.listview),
    path("<str:hashed_id>/", GuardrailDetailView.as_view(), name=GuardrailReverseNames.detailview),
]
```

The rules:

- **Every value is `to_snake_case(<ViewClass>.__name__)`**, for a class-based view, or
  `to_snake_case(<function>.__name__)` for a function view (`DashboardLogsApiReverseNames.stream`).
  Never a string literal.
- **`namespace` is the first attribute**, and is the module's namespace, without a trailing colon.
- **The attribute name is the role, not the class**: `listview`, `detailview`, `deployment_by_hashed_id`.
  It is what callers read, so it stays stable when a view is renamed.
- **`name=` in `urlpatterns` is always `<Class>.<attribute>`**, never a literal.
- **One view, several routes**: add a suffix to the derived name, so each route has its own name.
  `+ "_all"` for a variant, and the module constants `BY_ID = "_by_id"` and
  `BY_HASHED_ID = "_by_hashed_id"` for the same view by id and by hashed id. The suffix starts with an
  underscore. (`apps/llmclient/api/v1/urls.py` and `apps/vectorsearch/api/v1/urls.py` define them
  without one, which gives names such as `llm_client_viewby_id`: don't copy that.)
- **Name the class** `<App>ReverseNames` for console pages, `<App>ApiV1ReverseViews` for an api
  version. Both shapes are the same; only the suffix differs, for historical reasons.
- **Import the views at module level.** If that makes a circular import, put the class in a
  `names.py` beside `urls.py` and import it from both (`dashboard/views/terminal_emulator/names.py`).

`to_snake_case` splits acronyms as words: `LLMClientDeploymentView` → `llm_client_deployment_view`,
`MCPClientListView` → `mcp_client_list_view`. You never need to predict it, because you never type the
result.

### 3. Adding a route

1. Write the view class. Its name is the url name, so make it say what the page is.
2. Add an attribute to the module's `ReverseNames` class: `<role> = to_snake_case(<View>.__name__)`.
3. Add the `path(...)` with `name=<Class>.<role>`.
4. Reverse it as below, and test it through the attribute (`self.url("<role>", ...)`).

The workbench's Deployment tab is a worked example: `LLMClientDeploymentView`,
`PromptReverseNames.deployment_by_hashed_id`, the route `llm-clients/<str:hashed_id>/deployment/`, and
`PromptWorkbenchView.deployment_url`, which reverses it.

## Reversing

Use `smarter.lib.django.shortcuts.reverse`, not Django's, and always pass the class attributes.

**Without url kwargs, pass the namespaces and the name as separate arguments**; the wrapper joins them
with `:`:

```python
from smarter.lib.django.shortcuts import reverse

reverse(PromptReverseNames.namespace, PromptReverseNames.listview)
reverse(
    DashboardReverseNames.namespace,
    PassthroughReverseNames.namespace,
    PassthroughReverseNames.view,
)
```

**With url kwargs, pass one string, joined with an f-string.** The wrapper passes kwargs straight to
Django's `reverse`, so separate arguments would be taken as `urlconf`, `args`, ...:

```python
reverse(
    f"{PromptReverseNames.namespace}:{PromptReverseNames.deployment_by_hashed_id}",
    kwargs={"hashed_id": llmclient.hashed_id},
)
```

### From any host: `urlconf=settings.ROOT_URLCONF`

django-hosts serves a deployed LLMClient's host with `smarter.urls.llmclients`, which has none of the
console's names. Code that can run on such a host (a model property, a context processor, the page at a
deployed LLMClient's url) reverses against the platform's urlconf:

```python
from django.conf import settings

path = reverse(AuthTokenReverseNames.namespace, AuthTokenReverseNames.listview, urlconf=settings.ROOT_URLCONF)
```

The context processors wrap this as `console_reverse(*args)` (`apps/dashboard/context_processors.py`).

### Absolute urls

A url that leaves the console's own pages (an email, a page on an LLMClient's host, the cli's output)
is absolute, on the platform's domain. Follow `LLMClient.sandbox_url`, `manifest_url` and
`workbench_url`:

```python
path = reverse(
    f"{PromptReverseNames.namespace}:{PromptReverseNames.chat_by_hashed_id}",
    kwargs={"hashed_id": self.hashed_id},
    urlconf=settings.ROOT_URLCONF,
)
url = urljoin(smarter_settings.environment_url, path)
url = SmarterValidator.urlify(url, environment=smarter_settings.environment)
```

A url that a console page frames or fetches (Smarter Chat's `manifestEditorUrl`, `deploymentUrl`)
stays a path, so that it is of the page's own origin.

### Templates

A template can't import the class, so pass the url in the context, reversed in Python
(`sidebar_context()`, `PromptWorkbenchView`'s `smarter_chat` dict). Don't add `{% url 'ns:name' %}`
tags: they hard-code the derived string. The ones that remain (`console_home`, `account:account_login`,
`docs:openapi`, ...) are older.

### Tests

`ResourceViewsTestMixin` reverses through the class: set `reverse_names = <App>ReverseNames`, then
`self.url("<attribute>", **kwargs)`. In other tests, reverse through the class too, and assert the path
when the path itself is the contract (`"/workbench/llm-clients/<hashed_id>/deployment/"`).

## Legacy shapes: don't copy, fix when you're there anyway

| Where                                                                                       | What                                                                               | Instead                                                 |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `apps/account/urls.py`, `apps/account/views/dashboard/urls.py`                              | UPPER_CASE literal names (`ACCOUNT_LOGIN = "account_login"`), `DashboardNamedUrls` | `to_snake_case(<View>.__name__)`, lower-case attributes |
| `apps/prompt/api/v1/urls.py` (`PromptAPINamespace`), `apps/docs/urls.py`                    | literal names (`chathistory = "chathistory"`, `openapi = "openapi"`)               | derived names                                           |
| `apps/provider/api/v1/urls.py`, `apps/secret/api/v1/urls.py`, `apps/llmtool/api/v1/urls.py` | `name="..."` literals and no class                                                 | add the class                                           |
| `apps/api/v1/cli/urls.py` (`ApiV1CliReverseViews.namespace = "api:v1:cli:"`)                | a namespace with a trailing colon, used as `namespace + name`                      | no trailing colon; `f"{namespace}:{name}"`              |
| `ApiV1CliReverseViews.manifest` and `.example_manifest`                                     | two attributes with the same name                                                  | one attribute per route                                 |
| `apps/llmclient/api/v1/urls.py`, `apps/vectorsearch/api/v1/urls.py`                         | `BY_ID = "by_id"`, without the underscore                                          | `"_by_id"`, `"_by_hashed_id"`                           |
| `{% url 'console_home' %}` and other `{% url %}` tags                                       | hard-coded names in templates                                                      | reverse in Python, pass in the context                  |

Changing a name that is already released changes nothing for users (names are internal), but every
caller must change in the same commit. Grep for the attribute and for the literal string, including
templates and `react/` (a React app receives urls from its root element's attributes, never names).

## Checklist

- [ ] The namespace is a constant in the module's `const.py`; `app_name = namespace`.
- [ ] One `ReverseNames` class; `namespace` first, with no trailing colon.
- [ ] Every name is `to_snake_case(<View>.__name__)`, plus `_by_id` / `_by_hashed_id` / `_all` where
      one view has several routes.
- [ ] `name=` in every `path()` is a class attribute.
- [ ] Callers reverse through the class: variadic without kwargs, one f-string with kwargs, and
      `urlconf=settings.ROOT_URLCONF` where an LLMClient's host may be active.
- [ ] Templates get urls from the context, not `{% url %}`.
- [ ] A test reverses the new route through the class.
