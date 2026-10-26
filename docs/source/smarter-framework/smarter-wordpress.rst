Smarter Chat for WordPress
==========================

Smarter Chat for WordPress is a WordPress plugin that puts your Smarter chatbot, a deployed
:doc:`LLMClient <../smarter-resources/smarter-llmclient>`, on your WordPress site: a chat button in a
corner of every page, a **Smarter Chat** block, and a ``[smarter_chat]`` shortcode. The chat renders
in its own Shadow DOM, so your theme can't break it, and its look (logo, colors, fonts, avatars)
comes from the LLMClient's manifest, so you change it on Smarter, not in WordPress.

The plugin is a settings screen around the :doc:`embed script <smarter-chat/embedding>` of
``@smarter.sh/ui-chat``, which it ships, so that visitors' browsers load the chat from your site.
Its source is `github.com/smarter-sh/smarter-wordpress <https://github.com/smarter-sh/smarter-wordpress>`__.
It needs WordPress 6.5 or later and PHP 7.4 or later.


Set Up
------

1. **Deploy the LLMClient**, and allow your site's origin in its manifest, then apply it:

   .. code-block:: yaml

     spec:
       config:
         prompt:
           allowedOrigins:
             - https://www.example.com

   The plugin's settings screen shows your site's origin, to copy.

2. **Install the plugin.** Download ``smarter-chat-<version>.zip`` from the
   `latest release <https://github.com/smarter-sh/smarter-wordpress/releases>`__, and upload it in
   **Plugins → Add New → Upload Plugin**. Activate it.

3. **Configure it** in **Settings → Smarter Chat**: enter the LLMClient's url, e.g.
   ``https://stackademy.3141-5926-5359.api.example.com/``, and save.

The chat button now appears on every page of the site.


Placing the Chat
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Where
     - How
   * - Every page
     - **Show on every page**, in the settings, which is on by default. Choose the button's corner,
       label and color, and whether it starts open.
   * - A page, with blocks
     - Add the **Smarter Chat** block. Its settings, in the sidebar, are a chatbot url (empty means the
       one in the settings) and a height.
   * - A page, anywhere
     - ``[smarter_chat]``, or ``[smarter_chat chatbot="https://..." height="600px" width="100%"]``, in
       a classic editor, a page builder or a widget.

Pages without a chat load nothing. To show the button on some pages only, or to change its options in
code, use the plugin's filters in your theme's ``functions.php``:

.. code-block:: php

  // only on the front page
  add_filter( 'smarter_chat_show_launcher', 'is_front_page' );

  // a taller panel: the embed script's options, in camelCase
  add_filter( 'smarter_chat_launcher_config', function ( $config ) {
      $config['height'] = '700px';
      return $config;
  } );


Api Keys and Privacy
--------------------

An LLMClient without :doc:`api keys <../smarter-platform/api-keys>` is public, and needs none. If
yours has one, enter a Smarter api key in the settings. It is written into your pages, where any
visitor can read it, so use a key dedicated to the site, or prefer a public LLMClient with a
:doc:`budget <../smarter-resources/smarter-budget>`. The site's api key is sent only to the chatbot
in the settings, never to one that a post's shortcode names.

When a visitor opens the chat, their browser sends their messages, a session key and your site's
origin to the Smarter platform that hosts the chatbot. The chat keeps its session in a cookie,
``smarter_chat_<chatbot host>``. The plugin adds a suggested paragraph about both to WordPress's
privacy policy guide (**Settings → Privacy**).

The chat's script is served from your own site, from the copy that the plugin ships. Nothing
loads from a CDN.


Troubleshooting
---------------

The chat says it is not available, or the browser's console says "blocked by CORS policy": the site's
origin is not in the LLMClient's ``allowedOrigins``, or doesn't match it exactly, scheme, host and
port. For other symptoms, see :doc:`Embedding Smarter Chat <smarter-chat/embedding>`.
