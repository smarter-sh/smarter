Smarter Chat for Drupal
=======================

Smarter Chat for Drupal is a Drupal module, ``smarter_chat``, that puts your Smarter chatbot, a
deployed :doc:`LLMClient <../smarter-resources/smarter-llmclient>`, on a Drupal site: a chat button in
a corner of every page, and a **Smarter Chat** block for any region. The chat renders in its own
Shadow DOM, so your theme can't break it, and its look comes from the LLMClient's manifest.

The module is a settings form around the :doc:`embed script <smarter-chat/embedding>` of
``@smarter.sh/ui-chat``, which visitors' browsers load from jsDelivr, or from your site. Its source
is `github.com/smarter-sh/smarter-drupal <https://github.com/smarter-sh/smarter-drupal>`__. It needs
Drupal 10.3 or 11.


Set Up
------

1. **Deploy the LLMClient**, and allow your site's origin in its manifest's
   ``spec.config.prompt.allowedOrigins``, then apply it. The module's settings form shows the origin.

2. **Install the module** with Composer, and enable it:

   .. code-block:: console

     composer config repositories.smarter-drupal vcs https://github.com/smarter-sh/smarter-drupal
     composer require smarter-sh/smarter-drupal
     drush pm:install smarter_chat

3. **Configure it.** Grant **Administer Smarter Chat** to the roles that may set the chatbot. In
   **Configuration → Web services → Smarter Chat** (``/admin/config/services/smarter-chat``), enter
   the LLMClient's url, and save.

The chat button appears on every page that isn't an admin page. To put the chat in a region instead,
turn off **Show on every page**, and place the **Smarter Chat** block in Block layout or Layout
Builder, with Drupal's usual visibility rules. A block can name its own chatbot, height and width.


Configuration Management
------------------------

The settings are configuration, ``smarter_chat.settings``, so they deploy with
``drush config:export`` and ``config:import``. An api key, which an LLMClient needs only if it has
:doc:`api keys <../smarter-platform/api-keys>`, is public in the page anyway, but it shouldn't be
in git either: set it in ``settings.php``, which Drupal applies without exporting it:

.. code-block:: php

  $config['smarter_chat.settings']['api_key'] = getenv('SMARTER_API_KEY');

To host the chat's script yourself, copy ``dist/embed.js`` and ``dist/embed/`` of the npm package,
e.g. to ``/libraries/smarter-chat/``, and set **Advanced → Script url**. Modules can change the
launcher's options, or remove it from a page, with ``hook_smarter_chat_launcher_alter()``:

.. code-block:: php

  function mymodule_smarter_chat_launcher_alter(array &$launcher): void {
    if (\Drupal::service('path.matcher')->isFrontPage()) {
      $launcher = [];
    }
  }

Changes show on the next request, with Drupal's page caches on: everything the module renders
carries the settings' cache tag.
