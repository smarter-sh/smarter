Smarter Chat for Google Tag Manager
===================================

Smarter Chat for Google Tag Manager is a tag template that puts your Smarter chatbot, a deployed
:doc:`LLMClient <../smarter-resources/smarter-llmclient>`, on any site that has a
`Google Tag Manager <https://tagmanager.google.com>`__ web container, whatever the site is built
with: a chat button in a corner of the page, or the chat in an element of the page. Marketing and
analytics teams can add it, and change it, without a developer or a release of the site.

The template loads the :doc:`embed script <smarter-chat/embedding>` of ``@smarter.sh/ui-chat`` from
jsDelivr, in GTM's sandbox, with three narrow permissions. Its source is
`github.com/smarter-sh/smarter-gtm-template <https://github.com/smarter-sh/smarter-gtm-template>`__.


Add the Tag
-----------

1. In the LLMClient's manifest, allow the site's origin in ``spec.config.prompt.allowedOrigins``, and
   apply it.
2. In the container, **Templates → Tag Templates → Search Gallery**, find **Smarter Chat**, and add
   it, or **New → ⋮ → Import** this repository's ``template.tpl``.
3. **Tags → New → Smarter Chat**: enter the LLMClient's url, and choose the launcher's position,
   label and color. **Advanced → Target element** puts the chat in an element of the page, by its css
   selector, instead of a launcher.
4. Trigger it on **All Pages**. A single-page app can add **History Change**: a chatbot is added once
   per page, however many times the tag fires.
5. In the tag's **Advanced Settings → Consent Settings**, require ``functionality_storage``: the chat
   keeps its session in a cookie.
6. Preview the container, then publish it.

The template's permissions are: inject scripts from
``https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@*``; read and write ``SmarterChatConfig``, read
``SmarterChat.version`` and execute ``SmarterChat.mount``; and log to the console in Preview mode.
It reads no cookies and sends nothing itself. The **Embed script version** field (Advanced) is the
version that the template is tested with; set a range, such as ``0.9``, to follow patch releases.

An api key, which an LLMClient needs only if it has :doc:`api keys <../smarter-platform/api-keys>`, is
public in the page: use a key dedicated to the site.


A Custom HTML Tag
-----------------

Where a template can't be used, e.g. to host the script yourself, a **Custom HTML** tag with the
embed script's tag works too, without the sandbox:

.. code-block:: html

  <script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
    data-chatbot="https://stackademy.3141-5926-5359.api.example.com/" async></script>
