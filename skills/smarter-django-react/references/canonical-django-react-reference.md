# Canonical Django + React Reference

The Guardrail list page is the reference. Read these files together. Each one
names the others' identifiers, so read them as a set.

| Layer                                     | File                                                                                                                                                  |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sidebar URL                               | `smarter/smarter/apps/dashboard/context_processors.py` (`"guardrails": reverse(...)`)                                                                 |
| Sidebar link                              | `smarter/smarter/templates/dashboard/sidebar.html` (`{{ sidebar.guardrails }}`)                                                                       |
| URL names and routes                      | `smarter/smarter/apps/guardrail/urls.py` (`GuardrailReverseNames`)                                                                                    |
| Page view                                 | `smarter/smarter/apps/guardrail/views/listview/view.py`                                                                                               |
| List, clone, rename, delete api           | `smarter/smarter/apps/guardrail/views/listview/api.py`                                                                                                |
| Serializer (`can_delete`, `manifest_url`) | `smarter/smarter/apps/guardrail/serializers.py` and its base, `MetaDataWithOwnershipModelSerializer` in `smarter/smarter/apps/account/serializers.py` |
| Template tag                              | `smarter/smarter/apps/guardrail/templatetags/react_guardrail_list.py`                                                                                 |
| Template tag manager                      | `smarter/smarter/lib/django/templatetags/smarter_react_templatetag_manager.py`                                                                        |
| Template                                  | `smarter/smarter/templates/react/guardrail-list.html`                                                                                                 |
| React entry                               | `smarter/react/packages/smarter-guardrail-list/src/main.tsx`                                                                                          |
| React app                                 | `smarter/react/packages/smarter-guardrail-list/src/App.tsx` and `src/components/`                                                                     |
| Vite build and manifest                   | `smarter/react/packages/smarter-guardrail-list/vite.config.ts`                                                                                        |
| Shared React code                         | `smarter/react/packages/smarter-common/src/lib/{django,load,actionUrl,Types}.tsx` and `src/components/TabbedListView`                                 |
| Python tests                              | `smarter/smarter/apps/llmclient/tests/test_custom_domain_views.py` (`ResourceViewsTestMixin`)                                                         |

## The names that must agree

For a kind `widget`:

| Name                          | Where it appears                                                                                                                                                         |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `smarter-widget-list-root`    | the view's `root_id`, the template's `id=`, and `main.tsx`'s `getElementById`                                                                                            |
| `smarter-widget-list-api-url` | the template's attribute and `main.tsx`'s `getAttribute`                                                                                                                 |
| `widget_list`                 | the view's context key, and the template variables `{{ widget_list.* }}`                                                                                                 |
| `@smarter/widget-list`        | `package.json` `name`, the templatetag's `app_name`, and the static path `react/@smarter/widget-list/`                                                                   |
| `react_widget_list`           | the templatetag module, and `{% load react_widget_list %}`                                                                                                               |
| `widget_list_react_assets`    | the `@register.simple_tag` function in the templatetag module, returning `templatetag_manager.reactapp_build_assets`, used as `{% widget_list_react_assets as assets %}` |
