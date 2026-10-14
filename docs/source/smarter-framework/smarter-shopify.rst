Smarter Chat for Shopify
========================

Smarter Chat for Shopify puts your Smarter chatbot, a deployed
:doc:`LLMClient <../smarter-resources/smarter-llmclient>`, on a Shopify store, from the theme editor:
a chat button in a corner of every page of the storefront, and a **Smarter Chat** block for any
section. The chat renders in its own Shadow DOM, so the theme can't break it, and its look comes
from the LLMClient's manifest. With :doc:`plugins <../smarter-resources/smarter-plugin>` that read
your catalog, shipping and policies, it can answer shoppers' questions.

It is a Shopify app with one theme app extension and no server, which writes the tag of the
:doc:`embed script <smarter-chat/embedding>` of ``@smarter.sh/ui-chat``. Its source is
`github.com/smarter-sh/smarter-shopify <https://github.com/smarter-sh/smarter-shopify>`__.


Deploy the App
--------------

You deploy the app as your own store's app, with a `Shopify Partner <https://www.shopify.com/partners>`__
account and Node.js 22 or later:

.. code-block:: console

  git clone https://github.com/smarter-sh/smarter-shopify.git && cd smarter-shopify
  make init
  npx shopify app config link     # create the app in your Partner account
  npx shopify app deploy          # publish the theme app extension

Then install the app on your store from the Partner Dashboard.


Add the Chat to the Store
-------------------------

1. In the LLMClient's manifest, allow the store's origins, ``https://<store>.myshopify.com`` and its
   custom domains, in ``spec.config.prompt.allowedOrigins``, and apply it.
2. In the theme editor, **Theme settings → App embeds → Smarter Chat launcher**: turn it on, enter the
   LLMClient's url, and choose the button's corner, label and color.
3. Or, in any section, **Add block → Apps → Smarter Chat**, for the chat in a page, e.g. a Contact
   page, with its own height.

An api key, which an LLMClient needs only if it has :doc:`api keys <../smarter-platform/api-keys>`,
is public in the storefront: use a key dedicated to the store.


Without the App
---------------

A store that prefers not to install an app can paste the embed script's tag before ``</body>`` in
**Online Store → Themes → Edit code → layout/theme.liquid**:

.. code-block:: html

  <script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
    data-chatbot="https://shop-bot.3141-5926-5359.api.example.com/" async></script>

A theme update or a new theme loses it, which the app's embed doesn't.
