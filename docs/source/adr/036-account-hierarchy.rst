ADR-036: Account Hierarchy and Resource Sharing
================================================

Status
------
Proposed

Context
-------
Every resource that has an owner extends ``MetaDataWithOwnershipModel`` in ``smarter.apps.account.models``.
Its owner is a ``UserProfile``, the membership of one ``User`` in one ``Account``. A user may hold profiles in
several accounts, and may read the union of what each profile may read. Today one profile may read the
resources of:

1. its own account, and
2. the Smarter account, ``3141-5926-5359``, whose resources every account may read.

That second rule names one account in code, and it is the only way that resources are shared between
accounts. It has three consequences:

- **An organization can't be modeled as it is.** An ``Account`` may represent "a company, a course, a team, a
  department", but accounts have no relation to one another. A company whose departments are accounts can't
  give them shared services, such as the Secrets and Connections that its IT department manages, without
  publishing those to every account on the platform through the Smarter account.
- **The only shared-services account is the platform operator's.** A self-hosted installation's IT department
  must work as the Smarter admin to publish anything company-wide.
- **Plugins can't use a shared Connection at all.** ``SqlPlugin`` and ``ApiPlugin`` look up their Connection
  by name in the plugin owner's own account only (``smarter.apps.llmtool.plugin.sql`` and ``.api``). So
  ``manage.py initialize_account`` copies the whole Stackademy project, Secrets and Connections included, into
  every new account.

Stackademy, the fictional code academy in https://github.com/smarter-sh/stackademy, is Smarter's long-lived
demonstration of these features, and is being extended with back-office departments (HR, Accounting, Course
Content) that share an IT department's services. It is the worked example below.

Decision
--------
Accounts form a tree, and each account decides separately who may read its resources.

1. **``Account.parent``** is a nullable foreign key to another ``Account``, with ``on_delete=PROTECT``. The
   Smarter account is the root, and has no parent. Any other account whose ``parent`` is null is directly
   under the root, so every account is in the tree without a default to set, wherever it was created. An
   account may not be its own ancestor.
2. **``Account.share_scope``** is a nullable foreign key to the account itself or one of its ancestors. Null
   means that the account shares nothing. The tree describes the organization; ``share_scope`` describes
   sharing. Neither constrains the other, so an organization can be drawn as it really is (an IT department is
   a sibling of HR, not its parent) and still share with the right people.
3. **The read rule.** A user profile may read the resources of an account X if the profile's account is X, or
   descends from ``X.share_scope``. The Smarter account's ``share_scope`` is itself, so every account still
   reads it, and ``with_read_permission_for()`` no longer names it. A model's ``restrict_readable()`` still
   applies last, e.g. to the LLMClients that only the platform's staff may use.
4. **Read only, and downward only.** The tree grants read permission and nothing else: who may manage a
   resource doesn't change. A parent can't read its children's resources because it is their parent;
   a person who needs to, such as a chief financial officer, holds a profile in each account. The tree is
   inheritance; profiles are membership.
5. **Name resolution, nearest first, in the owner's tree only.** Where one resource names another (a plugin
   its Connection, an LLMClient its Proxy), the name is looked up in order: the owner's own profile, the
   owner's account, then the accounts that share with it, nearest ``share_scope`` first. The first match
   wins, so a department may override a shared resource by giving its own the same name. Only the owning
   profile's account tree counts, never what its user may read otherwise: a superuser reads every account,
   and a user with several profiles reads all of their accounts, but a plugin that an HR member wrote must
   find the same Connection as one that the CEO wrote, or HR's members would read, through the plugin,
   whatever its author can. One helper, ``smarter.apps.account.hierarchy.resolve_by_name()``, does this for
   every kind (:doc:`ADR-033 <033-dry>`), and replaces the per-kind lookups of ``SqlPlugin``, ``ApiPlugin``
   and the Proxy precedence in ``smarter.apps.proxy.services``.
6. **Who may change the tree.**

   - Setting an account's ``parent`` requires management permission in both the account and its new parent.
     Otherwise any account could make itself the child of another and read what that one shares with its
     descendants.
   - Setting ``share_scope`` requires management permission in the account itself, because it publishes the
     account's own resources.
   - A ``share_scope`` of the root, which publishes to every account on the platform, requires a superuser.

   Today only a superuser may apply an ``Account`` manifest, so these hold on that path. Any path that lets
   others change the tree, such as a web console page, must enforce them.

7. **Caching.** The read rule runs on nearly every request, and the tree changes a few times a year. For each
   account, ``smarter.apps.account.hierarchy.readable_account_ids()`` computes the ids of the accounts it may
   read, nearest first, and caches them with ``@cache_results`` (:doc:`ADR-018 <018-caching>`) for an hour.
   ``Account.save()`` and ``Account.delete()`` invalidate every account's entry when ``parent`` or
   ``share_scope`` changes, so the hour only bounds a direct database edit that bypasses them. The read rule
   is then a single ``user_profile__account_id__in`` filter on the cached list, and name resolution orders by
   the same list. Each app's own per-user caches of resource lists, such as a user's shared resources in the
   web console, keep their usual timeout, and catch up with a change to the tree within it.
8. **Manifests.** The ``Account`` manifest gains ``parent`` and ``shareScope``, each an account number, so an
   organization's tree is declared and versioned like any other resource. The ``User`` manifest gains
   ``spec.accounts``, a list of the accounts that the user belongs to, each with ``isAccountAdmin``, so that its
   people and their roles are declared the same way. Apply adds the memberships that are missing and updates the
   others, but never removes one: deleting a profile deletes every resource that it owns. A superuser may list any
   account; anyone else only the accounts that they administer.
9. **Migration.** ``account`` is a released app that holds production data, so the fields are added in new
   migrations (:doc:`ADR-020 <020-semantic-versioning>`): ``0014_account_hierarchy`` adds them, and
   ``0015_root_account_shares_with_everyone`` sets the Smarter account's ``share_scope`` to itself.
   ``Account.save()`` does the same when ``initialize_platform`` creates the Smarter account on a new
   platform. Every other account keeps a null ``parent`` and ``share_scope``, so every user reads exactly
   what they read before.

10. **Account administrators.** ``UserProfile.is_account_admin`` makes a user the administrator of that one
    account: they manage every resource in it, apply its Secrets, Connections, plugins and users, and may have
    an api key for it. It gives no rights in the user's other accounts, and no access to the Django admin site.
    ``User.is_staff``, which had been the only mark of an account's administrator, keeps its meaning: it
    administers every account the user belongs to, and opens the Django admin site, so it is for the platform's
    own staff, not for a department's administrator. One function, ``user_administers_account()`` in
    ``smarter.apps.account.models.user_profile``, decides it for the ownership rule, every broker's check, and
    api keys.

    - Only a superuser or a staff user may change a user's ``is_staff``, so an account's administrator can't
      make themselves, or anyone, staff.
    - A User manifest names its user by username, across the whole platform, so applying one to a user who
      doesn't belong to the applier's account is refused, unless a superuser applies it.

The other meanings of the Smarter account, such as its admin user, billing, ``initialize_platform`` and the
staff-only LLMClients, are about the platform's operator, not about sharing, and are not affected.

Worked example: Stackademy
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 24 20 20 36

   * - Account
     - ``parent``
     - ``share_scope``
     - Who may read its resources
   * - Smarter (the platform)
     - none
     - itself
     - Every account.
   * - Stackademy Corp
     - none (the root)
     - none
     - Its own members, e.g. the CEO.
   * - Stackademy IT
     - Stackademy Corp
     - Stackademy Corp
     - All of Stackademy, but no other company on the platform.
   * - Stackademy HR
     - Stackademy Corp
     - none
     - HR's members only.
   * - Stackademy Europe
     - Stackademy Corp
     - Stackademy Europe
     - Its own departments, which also read Stackademy IT's resources.
   * - Pixel Forge Studios
     - none (the root)
     - none
     - Its own members. Its video editors also hold profiles in Stackademy Content.

HR's ``SqlPlugin`` names the Connection ``stackademy_hr``, which Stackademy IT owns. The plugin finds it, and
its Secret, in Stackademy IT. A user in Pixel Forge Studios can't read either, and neither can Accounting's
members, whose own Connection's database user has no grant on HR's tables.

Alternatives Considered
-----------------------
- **A boolean ``is_system_wide`` flag** in place of the hard-coded account number. It removes the special case,
  but every flagged account is visible to every account on the platform, so a company can't share with its own
  departments only.
- **``parent`` plus a boolean ``is_shareable``.** A boolean still has to mean "shared with my descendants",
  which gives an IT department that is a sibling of HR no way to share with it, or "shared with my parent's
  descendants", which makes a shareable top-level company visible to every account. ``share_scope`` names the
  audience, and the boolean is its special case ``share_scope = parent``.
- **Teams or groups inside an account.** A second hierarchy beside the accounts, with its own membership,
  permissions and console pages. Accounts already carry membership, billing, budgets, currency, time zone and
  language, all of which an organization's units need.
- **A materialized path or nested sets** (``django-treebeard``, ``django-mptt``) to query ancestors in SQL.
  The tree is small and rarely changes, so caching each account's readable accounts is simpler, and adds no
  dependency.
- **Let the tree grant management permission** to a parent's staff. Convenient for an organization's
  administrators, but it turns every reorganization into a change of who may edit what. It can be decided
  separately, later.

Consequences
------------
- **Positive:**

  - An organization's accounts can be drawn as the organization really is, and shared services kept in the
    account of the department that runs them, visible to exactly the accounts that need them.
  - The read rule no longer names an account. The Smarter account is the root of the tree, shared like any
    other.
  - Plugins can use shared Connections, so ``initialize_account`` no longer needs to copy Secrets and
    Connections into every account.
  - Budgets, billing and reports can later roll up by subtree.

- **Negative:**

  - The read rule depends on a cache, so a change to the tree that misses an invalidation shows stale
    permissions. Invalidation is tested, and is all or nothing, to keep that risk small.
  - Name resolution across accounts can surprise: a resource found by name may belong to another account.
    Each resolved reference's owner is shown in the console and logged by id.
  - Every kind that resolves another by name changes to the shared helper, and needs tests for each order of
    precedence.
  - Moving an account under a new parent needs the consent of both, which the web console and the
    ``Account`` broker must enforce.

Related ADRs
------------
- :doc:`ADR-016: Security <016-security>`
- :doc:`ADR-018: Caching <018-caching>`
- :doc:`ADR-020: Semantic Versioning <020-semantic-versioning>`
- :doc:`ADR-024: Broker Model <024-broker-model>`
- :doc:`ADR-033: Don't Repeat Yourself <033-dry>`
