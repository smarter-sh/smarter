Smarter Chat for Documentation Sites
====================================

A documentation site is where a product's users ask questions, and a Smarter
:doc:`LLMClient <../smarter-resources/smarter-llmclient>` with the docs in a
:doc:`vectorstore <../smarter-resources/smarter-vectorstore>` can answer them on the page. One setting
adds its chat button to every page of a site built with Docusaurus, MkDocs (with any theme, including
Material for MkDocs), Sphinx (with any html theme, including Read the Docs' and Furo) or VitePress.
The chat renders in its own Shadow DOM, so the site's theme can't break it, and it survives the
client-side navigation of Docusaurus, Material and VitePress.

Each integration writes the tag of the :doc:`embed script <smarter-chat/embedding>` of
``@smarter.sh/ui-chat``, with the same options, and fails the site's build if the chatbot's url is
missing or invalid. Their source is
`github.com/smarter-sh/smarter-docs-site-generators <https://github.com/smarter-sh/smarter-docs-site-generators>`__.
In every case, first allow the site's origin (e.g. ``https://<project>.readthedocs.io``) in the
LLMClient's ``spec.config.prompt.allowedOrigins``, and apply its manifest.


Docusaurus
----------

.. code-block:: console

  npm install @smarter.sh/docusaurus-plugin-smarter-chat

.. code-block:: js

  // docusaurus.config.js
  export default {
    plugins: [["@smarter.sh/docusaurus-plugin-smarter-chat", { chatbot: "https://docs-bot.example.com/" }]],
  };


MkDocs and Material for MkDocs
------------------------------

.. code-block:: console

  pip install mkdocs-smarter-chat

.. code-block:: yaml

  # mkdocs.yml
  plugins:
    - search
    - smarter-chat:
        chatbot: https://docs-bot.example.com/


Sphinx
------

.. code-block:: console

  pip install sphinx-smarter-chat

.. code-block:: python

  # conf.py
  extensions = ["sphinx_smarter_chat"]
  smarter_chat_chatbot = "https://docs-bot.example.com/"

On Read the Docs, add ``sphinx-smarter-chat`` to the docs' requirements file. Every option is a config
value prefixed ``smarter_chat_``.


VitePress
---------

VitePress needs no package: one ``head`` entry in ``.vitepress/config.mts``.

.. code-block:: ts

  export default defineConfig({
    head: [["script", {
      src: "https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0.9.0/dist/embed.js",
      "data-chatbot": "https://docs-bot.example.com/",
      async: "",
    }]],
  });


Options
-------

The same options in every integration, named in its own style (``apiKey`` in JavaScript,
``api_key`` in YAML and Python, ``data-api-key`` in VitePress's tag):

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Option
     - Default
     - Description
   * - ``chatbot``
     - (required)
     - The deployed LLMClient's url.
   * - ``apiKey``
     -
     - Only for an LLMClient that has :doc:`api keys <../smarter-platform/api-keys>`. It is public in
       the pages.
   * - ``position``
     - ``bottom-right``
     - ``bottom-right`` or ``bottom-left``.
   * - ``label``, ``color``
     - ``Chat``, ``#ff5733``
     - The button's accessible name and color.
   * - ``open``
     - ``false``
     - Start open.
   * - ``height``, ``width``
     - ``600px``, ``400px``
     - The panel's size.
   * - ``version``
     - the integration's
     - The version of ``@smarter.sh/ui-chat`` to load from jsDelivr, or a range, e.g. ``0.9``.
   * - ``src``
     -
     - The url or path of a self-hosted ``embed.js``, with its ``embed/`` directory beside it.


Other Generators
----------------

Any other generator (Hugo, Jekyll, Astro, Eleventy) takes the embed script's tag in its base
template, before ``</body>``:

.. code-block:: html

  <script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
    data-chatbot="https://docs-bot.example.com/" async></script>
