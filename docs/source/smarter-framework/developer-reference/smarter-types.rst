Smarter Types
=============

The platform and the :doc:`Smarter Python SDK <../smarter-python>` must agree on which kinds of
:doc:`manifest <../smarter-manifests>` exist, which commands the :doc:`cli api <../smarter-api/cli>`
has, and what the :doc:`Smarter Journal <smarter-journal>` records. Both take these definitions from
one package, `smarter-types <https://pypi.org/project/smarter-types/>`__, which is plain Python, with
no Django and no Pydantic, and has its own documentation at
`docs.smarter-types.smarter.sh <https://docs.smarter-types.smarter.sh/>`__. It holds:

- :class:`~smarter_types.kinds.SAMKinds`, every kind of Smarter Application Manifest, and the single
  definition of which kinds exist. It also gives the order in which manifests of several kinds are
  applied, :meth:`~smarter_types.kinds.SAMKinds.apply_order`, so that a Secret exists before the
  Connection that uses it, and a Connection before its plugin.
- :class:`~smarter_types.journal.SmarterJournalThings`, the things the journal records, and
  :class:`~smarter_types.journal.SmarterJournalCliCommands`, the commands of the cli api, with the
  keys of the cli api's responses.
- :class:`~smarter_types.enum.SmarterEnumAbstract`, the base class of these enumerations.

Smarter lists the package in ``smarter/requirements/in/base.in``, and ``make python-requirements``
pins its version. Smarter re-exports each class from the module that defined it before the package
existed, so platform code imports them as it always has: :mod:`smarter.apps.api.v1.manifests.enum`
(``SAMKinds``), :mod:`smarter.lib.journal.enum` (the journal's enumerations) and
``smarter.common.enum`` (``SmarterEnumAbstract``).

To add a resource kind, add it to ``SAMKinds`` in
`smarter-types <https://github.com/smarter-sh/smarter-types>`__ first, with its place in the apply
order, and release the package. Then run ``make python-requirements`` here to pick up the new
version, and give the kind an icon in :data:`~smarter.apps.api.v1.manifests.enum.SAM_KIND_ICONS`.
