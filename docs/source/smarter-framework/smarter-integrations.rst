Smarter Integrations
====================

The integrations put a deployed :doc:`LLMClient </smarter-resources/smarter-llmclient>`'s chat on
sites that are built on other platforms: a WordPress, Drupal or Shopify site, any site with a Google
Tag Manager container, and documentation sites built with Docusaurus, MkDocs, Sphinx or VitePress.
They are for the people who run those sites, who generally don't program against Smarter. Each one
adds the chat from a settings screen, so a site owner needs no code and no knowledge of Smarter
beyond the address of their LLMClient.

The integrations don't call the :doc:`Smarter API </smarter-framework/smarter-api>` themselves. Each
one is built on :doc:`Smarter Chat </smarter-framework/smarter-chat>`'s
:doc:`embed script </smarter-framework/smarter-chat/embedding>`, one ``<script>`` tag that any web
page can use, and writes that tag for you. The chat renders in its own Shadow DOM, so the site's
theme can't break it, and its look (logo, colors, fonts, avatars) comes from the LLMClient's
manifest, so you change it on Smarter, not on the site.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Integration
     - What it is
   * - :doc:`Smarter Chat for WordPress <smarter-integrations/smarter-wordpress>`
     - A WordPress plugin that adds the chat to a WordPress site: a launcher on every page, a block
       and a shortcode.
   * - :doc:`Smarter Chat for Drupal <smarter-integrations/smarter-drupal>`
     - A Drupal module that adds the chat to a Drupal site: a launcher on every page, and a block.
   * - :doc:`Smarter Chat for Shopify <smarter-integrations/smarter-shopify>`
     - A Shopify app whose theme app extension adds the chat to a store, from the theme editor.
   * - :doc:`Smarter Chat for Google Tag Manager <smarter-integrations/smarter-gtm>`
     - A tag template that adds the chat to any site with a Google Tag Manager container.
   * - :doc:`Smarter Chat for Documentation Sites <smarter-integrations/smarter-docs-sites>`
     - Plugins for Docusaurus, MkDocs and Sphinx, and a recipe for VitePress, that add the chat to
       every page of a documentation site.

For a site on another platform, paste the embed script's tag into its pages yourself, as
:doc:`Embedding Smarter Chat </smarter-framework/smarter-chat/embedding>` describes. To build the chat
into your own web application instead, use the React component in
:doc:`Smarter Chat </smarter-framework/smarter-chat>`.


.. toctree::
   :maxdepth: 1
   :caption: Integrations

   smarter-integrations/smarter-wordpress
   smarter-integrations/smarter-drupal
   smarter-integrations/smarter-shopify
   smarter-integrations/smarter-gtm
   smarter-integrations/smarter-docs-sites
