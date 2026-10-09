Natural Language Processing (NLP)
==================================

A plugin whose selector directive is ``search_terms`` is selected for a prompt that refers to
one of its search terms. :py:func:`smarter.apps.plugin.nlp.does_refer_to` decides, trying
three kinds of matching in turn, and stopping at the first that succeeds:

1. **Exact**: the prompt contains every word of the search term, in any order, ignoring case,
   punctuation and plurals. ``Tell me about Gobstoppers`` refers to ``Gobstopper``. This is
   always on.
2. **Fuzzy**: the prompt contains the search term with a typo or two, depending on its length.
   ``Who is Lawrance McDaniel?`` refers to ``Lawrence McDaniel``. The
   ``enable_plugin_fuzzy_matching`` waffle switch,
   :py:attr:`~smarter.lib.django.waffle.SmarterWaffleSwitches.ENABLE_PLUGIN_FUZZY_MATCHING`,
   controls it, and is on by default.
3. **Thesaurus**: the prompt contains a synonym of the search term, or of each of its words,
   from the `WordNet <https://wordnet.princeton.edu/>`__ thesaurus. ``I want to buy an
   automobile`` refers to ``car``, and ``a monochrome photograph`` refers to ``black and
   white``. The ``enable_plugin_thesaurus_matching`` waffle switch,
   :py:attr:`~smarter.lib.django.waffle.SmarterWaffleSwitches.ENABLE_PLUGIN_THESAURUS_MATCHING`,
   controls it, and is on by default.

Plugin selectors try exact and fuzzy matching on the prompt and on every user message first,
and thesaurus matching last, on the prompt only.

Thesaurus matching
------------------

Thesaurus matching selects plugins more often than the others, since a word has many synonyms.
To turn it off, if it selects plugins for prompts that do not need them, use Django admin, under
*Waffle > Switches*, or:

.. code-block:: bash

    python manage.py waffle_switch enable_plugin_thesaurus_matching off

To keep plugin selection precise, synonyms come only from the two most common senses of each
word, and only from its noun senses if it is a noun, since search terms are almost always
nouns. For example, the verb ``image`` means ``see``, so ``Let me see the code`` does not refer
to ``image``. Words of fewer than three letters, mostly pronouns and abbreviations, must match
exactly. WordNet does not know brand names, product names or most abbreviations, such as
``admin``, so search terms like these only match exactly, or with a typo.

WordNet is read with `NLTK <https://www.nltk.org/>`__, whose corpus data the Docker image
installs into ``/home/smarter_user/nltk_data``. Elsewhere, install it with
``python -m nltk.downloader wordnet``. Without it, thesaurus matching is disabled, with a
warning in the log.

Observability
-------------

Each successful match sends the
:py:data:`~smarter.apps.plugin.signals.search_term_matched` signal, with the prompt, the search
term, the kind of matching that succeeded (``exact``, ``fuzzy`` or ``thesaurus``), and, for a
thesaurus match, the synonym that matched. The plugin app's receiver logs it, so that you can
see why each plugin was selected.

Technical Reference
-------------------

.. automodule:: smarter.apps.plugin.nlp
    :members:
    :undoc-members:
    :show-inheritance:
