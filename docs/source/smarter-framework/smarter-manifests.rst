Smarter API Manifests (SAM)
=============================

Smarter provides declarative AI resource management, and Smarter API Manifests (SAM) are the declarations.
A manifest states what an AI resource should be (an LLMClient, a Plugin, a Guardrail, a Secret) and not
the steps needed to build it. You apply the manifest, and Smarter makes the resource match it: it creates the
resource if it does not exist and updates it if it does. Applying the same manifest twice gives the same result
(ie it is idempotent), so manifests can be kept in version control, reviewed like code, and
applied repeatedly across environments. The model is the one that `Kubernetes <https://kubernetes.io/>`__
made familiar, and SAM manifests are deliberately shaped like the manifests that ``kubectl apply`` accepts.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/smarter-manifest.png
  :alt: Example of a Smarter API Manifest
  :width: 100%

Behind each declaration, the Smarter API does the imperative work: database writes, AWS cloud infrastructure
operations and Kubernetes orchestration. You and your team describe the desired state of your AI resources, and
the platform works out how to get there.

Every manifest is validated against a strongly typed schema built with `Pydantic <https://docs.pydantic.dev/>`__.
Each resource kind has its own Pydantic model, so a manifest with a missing field, a wrong type or an invalid value
is rejected with a precise error before anything is changed. The same models generate the JSON Schema that the
Smarter API publishes for each kind.

Smarter manifests are utf-8 text documents, formatted as either YAML or JSON. The Smarter API that accepts them is
described by an `OpenAPI Specification v3.x <https://spec.openapis.org/oas/latest.html>`__ document. The manifest
framework, its Pydantic models, loader and brokers, is located in
`smarter/lib/manifest <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/lib/manifest>`__, and the API
that applies manifests in `smarter/apps/api <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/api>`__.
The Smarter API can manage `escaped <https://en.wikipedia.org/wiki/Escape_character>`__ representations of characters
outside of the utf-8 standard.

Manifest Structure
------------------

The basic structure of a Smarter API Manifest (SAM) YAML document includes the following key sections:

- **apiVersion**: Specifies the version of the API schema that the manifest adheres to, ``smarter.sh/v1``.
- **kind**: Indicates the type of resource being defined, for example ``Account``, ``LLMClient``, ``SqlPlugin``,
  ``Secret`` or ``Guardrail``. Each kind has a page under :doc:`/smarter-resources`.
- **metadata**: Identifies and describes the resource: its ``name``, ``description``, ``version``, ``tags`` and
  ``annotations``. Every kind shares these fields, and some kinds add their own, for example a plugin's
  ``pluginClass``. See `Metadata`_ below.
- **spec**: Defines the desired state and configuration of the resource. The spec section varies considerably by resource kind.
- **status**: (Optional) Provides information about the current state of the resource. This section is read-only and managed by the system.
  Its ``recordLocator``, e.g. ``llmclient-rMTAwMDAxMwx``, identifies the resource's row, and leads to its page in
  the web console. A broker's ``dependency_tree()`` lists, recursively and by record locator, every resource
  that a resource uses: an LLMClient's Provider, its plugins, their Connections, and those Connections'
  Secrets. See :doc:`smarter-manifests/record-locators`.

.. code-block:: yaml

    apiVersion: smarter.sh/v1
    kind: LLMClient
    metadata:
      name: stackademy_sql
      description: Stackademy University course catalogue inquiries using the Stackademy SQL plugin.
      version: 1.0.0
      tags:
        - stackademy
        - sql
      annotations:
        acme.com/finance/cost-center: "4410"
        acme.com/support/owner: data-platform-team
    spec:
      # the LLMClient's configuration

In addition to this basic structure, there are also a number of important style conventions that
Pydantic helps to enforce for SAM manifests:

- YAML fields use ``camelCase`` naming convention.
- Resource names, and values that in effect are foreign keys, that is, references to other resources by name,
  use ``snake_case`` naming convention.

Pydantic is also instrumental in validating the rules and relationships between individual fields
within a manifest, ensuring that manifests are well-formed and adhere to the expected structure. The Smarter API
must be able to read, validate, and correctly execute the commands necessary to bring the real-world
resources defined in the manifests in sync to the declaration of the manifest.

Metadata
--------

Every kind's metadata is validated by
:class:`~smarter.lib.manifest.models.AbstractSAMMetadataBase`, and stored on the resource's Django model by
:class:`~smarter.lib.django.models.metadata_model.MetaDataModel`, the base class of every resource model.

- **name** (required): the resource's name, unique among the resources of its kind that the same user owns. It must be URL-friendly and
  less than 50 characters long. Smarter converts it to ``snake_case``, and logs a warning when it does.
- **description**: a brief description of the resource, ideally under 255 characters. The key is required, but its
  value may be empty.
- **version**: a `semantic version <https://semver.org/>`__, for example ``1.0.0``. The key is required, but its
  value may be empty.
- **tags** (optional): a list of short labels. See `Tags`_.
- **annotations** (optional): a map of keys to string values, as in Kubernetes. See `Annotations`_.

Tags
~~~~

Tags are short, free-form labels that categorize resources, for example by project, team or environment:

.. code-block:: yaml

    metadata:
      tags:
        - stackademy
        - production

Each tag must consist of URL-friendly characters, and may contain spaces. Smarter stores tags with
`django-taggit <https://django-taggit.readthedocs.io/>`__, so they are shared across resources, and any Django code
can find the resources that carry a tag:

.. code-block:: python

    from smarter.apps.llmclient.models import LLMClient

    LLMClient.objects.filter(tags__name="production")

Tags answer the question "which resources belong to this group?". They hold no values. Use annotations when you
need to attach data to a resource.

.. _sam-annotations:

Annotations
~~~~~~~~~~~

Annotations attach your own data to a resource, as a map of keys to string values. They work as
`annotations do in Kubernetes <https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/>`__,
and serve the same purpose: they let other software associate a resource with something it knows about, for
example the record that mirrors it in a CRM or a CMDB, or a setting that a legacy system should apply to it.

.. code-block:: yaml

    metadata:
      annotations:
        acme.com/crm/account-id: A-10042
        acme.com/finance/cost-center: "4410"
        acme.com/compliance/reviewed: "true"
        acme.com/support/runbook: |
          Page the data platform on-call engineer.
          Escalate to the vendor after 30 minutes.

The rules are those of Kubernetes, with one extension:

- **Keys** are ``prefix/name``. The prefix is optional, and is a lowercase DNS subdomain of at most 253
  characters, such as ``acme.com``, that names who owns the key. The name is one or more segments separated by
  slashes, such as ``crm/account-id``. Kubernetes allows only one segment. Each segment is at most 63 characters,
  begins and ends with a letter or digit, and may contain ``-``, ``_`` and ``.`` in between. Every valid
  Kubernetes key is a valid Smarter key. Smarter keeps the case of keys, unlike the rest of the manifest, which
  it converts between ``camelCase`` and ``snake_case``.
- **Values** are strings, including multi-line YAML block scalars. Quote values that YAML would read as another
  type, as Kubernetes requires. Smarter is more forgiving: it converts unquoted booleans, numbers and dates to the
  strings that were written, so ``reviewed: true`` is stored as ``"true"``. Lists and maps are rejected. To store
  structured data, write it as a JSON string.
- A key may appear only once. All of a resource's annotations together, keys and values, are limited to 256 KiB.
- The prefix ``smarter.sh``, and its subdomains, belong to the Smarter platform, as ``kubernetes.io`` belongs to
  Kubernetes. Smarter's own manifests use it. Manifests may carry these keys, but use a domain that your
  organization controls for your own.

Older manifests write annotations as a list of one-key maps, ``- acme.com/crm/account-id: A-10042``. Smarter
still accepts that form, and returns annotations as a map.

``apply`` makes a resource's annotations exactly those of its manifest, as ``kubectl apply`` does: keys that the
manifest no longer has are removed. ``smarter describe`` and the ``api/v1/cli/describe/`` endpoint return them.

Smarter stores each annotation as a row of :class:`~smarter.lib.annotation.models.Annotation`, so that it can
find resources by their annotations quickly, with an annotation selector. Its syntax is that of
`Kubernetes label selectors <https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#label-selectors>`__,
one requirement at a time:

=================================  ========================================================
Requirement                        Matches the resources whose annotation
=================================  ========================================================
``acme.com/crm/account-id``        exists, with any value
``!acme.com/crm/account-id``       doesn't exist
``acme.com/crm/account-id=A-1``    has the value ``A-1``
``acme.com/crm/account-id!=A-1``   doesn't exist, or has another value
=================================  ========================================================

The ``api/v1/cli/get/<kind>/`` endpoint takes a selector as its ``annotation`` query parameter, which may be
repeated. Every requirement must match. The web console's list pages and dashboard search take the same
selectors (see :doc:`/smarter-platform/smarter-web-console`):

.. code-block:: console

    curl -X POST -H "Authorization: Token $SMARTER_API_KEY" \
      "https://platform.example.com/api/v1/cli/get/LLMClient/?annotation=acme.com/crm/account-id=A-10042&annotation=!acme.com/archived"

Smarter itself never interprets annotation values. That is what makes them safe to extend: an annotation means
whatever the software that reads it decides it means, and no future Smarter release will change that.

Annotations are stored as plain text, and anyone who can describe the resource can read them. Don't put
credentials in annotations. Store them in a :doc:`Secret </smarter-resources/smarter-secret>`, and annotate the
resource with the secret's name if your integration needs to find it.

Integrating with Smarter: Annotations and Signals
--------------------------------------------------

Annotations, together with Django signals and receivers, are the principal means for other software engineering
teams to build robust integrations with the Smarter platform. They let your team attach its own data to Smarter
resources and act on it, without forking Smarter, changing its database schema, or waiting for a Smarter release:

- **Annotations carry your data.** The people who write a manifest declare, in the same document that defines the
  resource, how your systems should treat it, for example its cost center, its owning team, its data classification,
  or the identifier of the record that mirrors it in your CMDB. The data travels with the resource through
  ``apply``, ``describe``, version control and code review, like the rest of the manifest.
- **Annotation handlers tell you when your data changes.** A handler is a function that your Django app registers
  for a key prefix that it owns, such as ``acme.com``. Smarter calls it whenever an annotation with that prefix,
  or one of its subdomains, is added, changed or removed on any resource, including when the resource is deleted.
  This is what a controller that watches an annotation does in Kubernetes.
- **Signals tell you when to act.** Smarter sends a `Django signal <https://docs.djangoproject.com/en/stable/topics/signals/>`__
  at each significant event in a resource's life. A receiver, a function that your Django app connects to a signal,
  runs whenever the signal is sent, and receives the resource, from which it reads the annotations.
- **Queries find the resources.** Your code can ask which Smarter resources, of any kind, are associated with a
  record of yours, and your users can ask the same with an annotation selector.

Because Smarter never interprets annotations, and because handlers and receivers connect to Smarter rather than
change its code, your integration and the Smarter platform can each evolve independently.

Reading and Querying Annotations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every resource's model has an ``annotations`` property, a ``dict`` of strings, and the methods below. See
:doc:`/smarter-framework/developer-reference/lib/annotation` for the complete API.

.. code-block:: python

    from smarter.apps.llmclient.models import LLMClient
    from smarter.lib.annotation.models import Annotation
    from smarter.lib.annotation.selectors import filter_by_annotations

    llmclient.annotations.get("acme.com/crm/account-id")      # "A-10042", or None

    # assign the whole map, as apply does; save() adds, changes and removes rows to match.
    llmclient.annotations = {**llmclient.annotations, "acme.com/crm/account-id": "A-20000"}
    llmclient.save()

    # or change one key, immediately, without saving the resource's other fields.
    llmclient.set_annotation("acme.com/crm/synced", "true")
    llmclient.remove_annotation("acme.com/crm/synced")

    # the LLMClients that map to CRM account A-10042.
    LLMClient.with_annotation("acme.com/crm/account-id", "A-10042")

    # the same, with a selector, applied to the LLMClients that a user may read.
    filter_by_annotations(LLMClient.objects.with_read_permission_for(user), ["acme.com/crm/account-id=A-10042"])

    # every Smarter resource, of any kind, that maps to CRM account A-10042.
    Annotation.objects.with_key("acme.com/crm/account-id", "A-10042").resources()

    # every annotation that your integration owns.
    Annotation.objects.with_prefix("acme.com")

``with_annotation()``, ``Annotation.objects`` and ``resources()`` don't check anyone's permissions. When you
answer a user, filter a queryset that does, as ``filter_by_annotations()`` above does.

Annotation Handlers
~~~~~~~~~~~~~~~~~~~

Register a handler for your prefix in your app's ``AppConfig.ready()`` method:

.. code-block:: python

    # acme_integration/handlers.py
    from smarter.lib.annotation.handlers import AnnotationEvent, annotation_handler

    from .tasks import link_crm_account, unlink_crm_account


    @annotation_handler("acme.com")
    def crm_account(event: AnnotationEvent) -> None:
        if event.change.key != "acme.com/crm/account-id":
            return
        if event.change.action == "removed":
            unlink_crm_account.delay(event.model_label, event.object_id, event.change.old_value)
        else:
            link_crm_account.delay(event.model_label, event.object_id, event.change.new_value)

A handler is called once for each changed annotation, with an
:class:`~smarter.lib.annotation.handlers.AnnotationEvent`: the resource (``instance``), its model
(``model_label``, e.g. ``llmclient.LLMClient``) and primary key (``object_id``), and the change
(``change.key``, ``change.action``, which is ``added``, ``changed`` or ``removed``, ``change.old_value`` and
``change.new_value``). ``resource_deleted`` is true when the resource itself was deleted. Handlers run after the
database transaction commits, so they never see a change that was rolled back. An exception in a handler is
logged, and affects neither the resource nor the other handlers.

Only Smarter's own code may register a handler for ``smarter.sh`` or its subdomains.

To see every change to every resource's annotations, whatever its prefix, connect a receiver to the
:data:`~smarter.lib.annotation.signals.annotations_changed` signal instead. It is sent once per resource, with
the list of its changes.

Which Signals to Use
~~~~~~~~~~~~~~~~~~~~

- **Annotation handlers and** ``annotations_changed`` are sent when annotations change, and only then. See
  `Annotation Handlers`_.
- **Django's model signals**, ``post_save`` and ``post_delete``, are sent for every resource kind, because every
  resource is a Django model. ``post_save`` is sent when ``smarter apply`` creates or updates a resource, and
  ``post_delete`` when ``smarter delete`` deletes it. The receiver gets the model instance as ``instance``.
- **Smarter's own signals** are sent at events that are specific to a kind, for example ``llmclient_called``,
  ``llmclient_deployed``, ``plugin_called``, ``guardrail_blocked``, ``budget_exceeded``, ``secret_accessed`` and
  ``provider_suspended``. Each app declares its signals in its ``signals.py`` module, for example
  :mod:`smarter.apps.llmclient.signals`, and documents their arguments there. Most pass the resource itself, for
  example ``llmclient=`` or ``guardrail=``.

See :doc:`Django Signals </smarter-framework/developer-reference/lib/django/signals>` for the basics, and
:doc:`Infrastructure </smarter-framework/technologies/infrastructure>` for the signals that the cloud
infrastructure services send.

Example
~~~~~~~

These receivers open a ticket in the owning team's queue each time an LLMClient is deployed, and post its cost
center to a finance system each time one is applied. An annotation handler for ``acme.com`` would post the cost
center only when it changes:

.. code-block:: python

    from django.db import transaction
    from django.db.models.signals import post_save
    from django.dispatch import receiver

    from smarter.apps.llmclient.models import LLMClient
    from smarter.apps.llmclient.signals import llmclient_deployed

    from .tasks import open_ticket, sync_cost_center


    @receiver(post_save, sender=LLMClient, dispatch_uid="acme_llmclient_saved")
    def handle_llmclient_saved(sender, instance, created, **kwargs):
        cost_center = instance.annotations.get("acme.com/finance/cost-center")
        if cost_center is None:
            return
        # apply saves inside a database transaction. Act after it commits.
        transaction.on_commit(lambda: sync_cost_center.delay(instance.pk, cost_center))


    @receiver(llmclient_deployed, dispatch_uid="acme_llmclient_deployed")
    def handle_llmclient_deployed(sender, llmclient, **kwargs):
        owner = llmclient.annotations.get("acme.com/support/owner")
        if owner:
            open_ticket.delay(queue=owner, subject=f"LLMClient {llmclient.name} was deployed")

Writing Robust Django Receivers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Register your app.** Put your receivers in a ``receivers.py`` module of your own Django app, import it from
  your ``AppConfig.ready()`` method, and add the app to ``INSTALLED_APPS``. See the
  :doc:`Developer Feature Checklist </smarter-framework/guides/developer-feature-checklist>`.
- **Keep receivers short, and fail safe.** Smarter sends its signals with ``send()``, so receivers run
  synchronously, in the web server or Celery worker process that sent the signal, and an exception that a receiver
  raises propagates to the operation that sent it. Catch your own errors, and hand slow work, such as calls to other
  systems, to a Celery task.
- **Act after the transaction commits.** ``apply`` saves a resource inside a database transaction. Use
  ``transaction.on_commit()``, as above, so that your integration never acts on a change that is rolled back.
- **Read tags after the save.** ``apply`` sets a resource's tags after it saves the resource, so a ``post_save``
  receiver can see the previous tags. To react to tag changes, connect to Django's ``m2m_changed`` signal.
  ``instance.annotations`` already holds the new annotations in a ``post_save`` receiver, but their rows are
  written just after it, so query ``Annotation.objects`` from an annotation handler, not from ``post_save``.
- **Be idempotent.** ``apply`` works like an upsert, so the same manifest can be applied many times, and
  ``post_save`` is sent each time. Use ``dispatch_uid`` so that each receiver is connected only once.
- **Treat missing annotations as normal.** Not every resource will carry your keys. Ignore resources that don't,
  and validate the values of those that do.

The modules and classes below establish the foundation of Smarter's SAM data models.

.. toctree::
   :maxdepth: 1
   :caption: Technical References

   smarter-manifests/example-manifest
   smarter-manifests/example-manifests
   smarter-manifests/stackademy
   smarter-manifests/enum
   smarter-manifests/pydantic-models
   smarter-manifests/sam-loader
   smarter-manifests/manifest-templates
   smarter-manifests/controller
   smarter-manifests/broker-model
   smarter-manifests/record-locators
   smarter-manifests/error-handling
   smarter-manifests/validation-strategy
