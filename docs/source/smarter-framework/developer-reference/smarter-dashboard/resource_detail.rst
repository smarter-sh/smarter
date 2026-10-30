Resource Detail
===============

When a row of a web console list is chosen, the list opens the resource's detail, a dialog of
``@smarter/common``'s ``ResourceDetail``. Its Details tab is the list's own ``DetailView``. Its
Manifest, Hierarchy and Dependencies tabs are fetched once, from the row's ``detailUrl``, which
:class:`~smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer` adds to every list
api's rows: ``/dashboard/api/resource/<kind>/<record locator>/``.

- **Manifest** is the resource's manifest, as ``smarter describe`` returns it to the resource's
  owner, as YAML.
- **Hierarchy** is :meth:`~smarter.lib.manifest.broker.AbstractBroker.dependency_tree`: every
  resource that it uses, recursively, drawn as the Prompt Engineer's Workbench's Architecture tab
  draws an LLMClient's.
- **Dependencies** is :meth:`~smarter.lib.manifest.broker.AbstractBroker.dependents`: the
  resources that use it, which keep it from being deleted.

A resource that the user may not read, in the hierarchy or among the dependents, is locked: it has
its kind and record locator only. A resource that the user may not read, or whose kind is not the
url's, has no detail: the api answers 404.

.. automodule:: smarter.apps.dashboard.resource_detail
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.dashboard.views.views.api.resource_detail
    :members:
    :show-inheritance:
