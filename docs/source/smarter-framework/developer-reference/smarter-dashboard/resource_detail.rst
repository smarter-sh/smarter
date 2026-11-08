Resource Detail
===============

When a row of a web console list is chosen, the list opens the resource's detail, a dialog of
``@smarter/common``'s ``ResourceDetail``. Its Details tab is the list's own ``DetailView``. Its
Manifest, Hierarchy and Dependencies tabs are fetched once, from the row's ``detailUrl``, which
:class:`~smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer` adds to every list
api's rows: ``/api/web/dashboard/resource/<kind>/<record locator>/``.

- **Manifest** is the resource's manifest, as ``smarter describe`` returns it to the resource's
  owner, as YAML.
- **Hierarchy** is :meth:`~smarter.lib.manifest.broker.AbstractBroker.dependency_tree`: every
  resource that it uses, recursively, drawn as the Prompt Engineer's Workbench's Architecture tab
  draws an LLMClient's.
- **Dependencies** is :meth:`~smarter.lib.manifest.broker.AbstractBroker.dependents`: the
  resources that use it, which keep it from being deleted.

Who may read a resource is its model's rule: its manager's ``with_read_permission_for()``, for an
owned resource, or the instance's ``is_readable_by()``, e.g. a Budget's, which a superuser may read,
and anyone else when it is attached to a resource whose budgets they may see. A model with neither
is read by nobody, so that a model without a rule can't leak through the api. A resource that has
no owner, e.g. a Budget, is described on behalf of the user who reads it.

A resource that the user may not read, in the hierarchy or among the dependents, is locked: it has
its kind and record locator only. A resource that the user may not read, or whose kind is not the
url's, has no detail: the api answers 404.

The same api serves the single-page console's manifest pages (:doc:`ADR-035 </adr/035-single-page-app>`),
e.g. ``/guardrail/guardrails/<hashed id>/``, which show a resource's manifest in the manifest editor,
where it can be validated, saved, cloned and deleted with the cli api. A page knows its model's record
locator prefix and the resource's hashed id (an api key's key id), so it asks
``/api/web/dashboard/resource/<record locator>/``, without a kind: the kind is the resource's own
``kind``, as a plugin's, or its model's, in ``KIND_BY_RECORD_LOCATOR_PREFIX``. Each page keeps its
Django view class and url name, a ``ConsoleAppView``, which
:func:`~smarter.lib.manifest.record_locator.console_paths` reverses for every resource's ``url``.

.. automodule:: smarter.apps.dashboard.resource_detail
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.dashboard.views.views.api.resource_detail
    :members:
    :show-inheritance:
