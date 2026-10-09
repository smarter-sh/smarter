Smarter Waffle
=================

Smarter's feature switches are defined in
:py:class:`~smarter.lib.django.waffle.SmarterWaffleSwitches`, and created, with their
defaults, by ``manage.py initialize_waffle``. Among them, two widen how plugin selectors match
their search terms: ``enable_plugin_fuzzy_matching``, on by default, tolerates typos, and
``enable_plugin_thesaurus_matching``, on by default, matches synonyms from the WordNet
thesaurus. See :doc:`Natural Language Processing <../../../../smarter-resources/plugin/nlp>`.

.. automodule:: smarter.lib.django.waffle
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: DbState, is_database_ready
