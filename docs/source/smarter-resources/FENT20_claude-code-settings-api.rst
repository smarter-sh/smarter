.. Claude Code settings API reference
   Renders the Google-style docstrings (ADR 029) of claude_code_settings.py.
   Intended location in the docs tree: smarter-resources/
   Created with the assistance of Claude (Anthropic), using our team's original
   ideas to meet the requirements of the capstone project for the AI Integration
   in Enterprise course.
   Build requirements (docs/source/conf.py):
     - extensions must include "sphinx.ext.autodoc" and "sphinx.ext.napoleon"
     - the folder containing claude_code_settings.py must be on sys.path

Claude Code Settings API
========================

.. note::

   **Acknowledgment.** This page was created with the assistance of Claude
   (Anthropic), using our team's original ideas to meet the requirements of the
   capstone project for the AI Integration in Enterprise course.
   
Reference for the ``claude_code_settings`` helper used in Part D of the
:doc:`Getting Started tutorial </smarter-resources/getting-started-claude-code>`.
It reads a Smarter ``Provider`` manifest and generates the matching Claude Code
``settings.json``.

.. note::

   The helper takes the model from the manifest. The gateway URL and API key
   are not part of the manifest, so you supply them. The API key is never
   written to disk unless you explicitly ask for it.

Module reference
----------------

.. automodule:: smarter.common.conf.FENT20_claude_code_settings
   :members:
   :undoc-members:
   :show-inheritance:

See also
--------

- :doc:`/smarter-resources/FENT20_getting-started-claude-code`
- :doc:`/smarter-resources/smarter-provider`
