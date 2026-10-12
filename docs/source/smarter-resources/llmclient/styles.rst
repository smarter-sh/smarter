Styling Your LLMClient's Chat
=============================

Every LLMClient comes with a chat window: in the Smarter workbench, where you test it, and on every web
page that embeds it with :doc:`Smarter Chat <../../smarter-framework/smarter-chat>`. Out of the box, that
window is a tidy blue and white. With a few lines in your manifest, it can wear your brand: your logo in
the corner, your colors on the message bubbles, your font, a picture behind the conversation, and a
friendly face beside each of the assistant's answers.

This page is written for prompt engineers. You don't need to be a web developer, and you don't need to
know CSS (the language that web pages use for their looks). Everything you need is explained here, with
examples you can copy.

.. contents:: On this page
   :local:
   :depth: 1


Where the Styles Go
-------------------

An LLMClient's manifest has two parts under ``spec.config``:

- ``prompt`` (required) is what the LLMClient *is*: its LLM provider and model, its system prompt, and
  the words of its chat, such as its name, welcome message, example prompts and placeholder.
- ``styles`` (optional) is how its chat *looks*.

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: LLMClient
   metadata:
     name: stackademy_sql
     description: Stackademy's course advisor.
     version: 1.0.0
   spec:
     config:
       prompt:
         provider: openai
         defaultModel: gpt-6-luna
         appName: Stackademy
         appAssistant: Stanley
         appWelcomeMessage: Welcome to Stackademy! How can I help you today?
       styles:
         appLogoUrl: https://cdn.example.com/stackademy/logo.png
         outgoingMessage:
           backgroundColor: "#fca311"

That's a complete styling: a logo, and the user's messages in Stackademy's amber. Every setting in
``styles`` is optional. Anything you leave out keeps its default look, so you can start with one line
and add more as you go.

Apply the manifest as usual, then reload the LLMClient's chat in the workbench to see the result:

.. code-block:: console

   smarter apply -f stackademy.yaml


The Parts of the Chat
---------------------

The chat window is made of a few parts, and ``styles`` has a section for each. The section names are
the names that the chat's building blocks use (see `Under the Hood`_), so they're the same ones you'll
see in the chat's technical documentation.

.. raw:: html

   <div style="max-width: 460px; margin: 1em auto 1.5em; font-family: Helvetica, Arial, sans-serif; font-size: 14px; color: #212121;">
     <div style="border: 2px solid #f15a29; border-radius: 6px; overflow: hidden; background: #fff;">
       <div style="display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #14213d; color: #fff; border-bottom: 1px solid #d1dbe3;">
         <div style="width: 38px; height: 38px; border-radius: 50%; background: #fff; display: flex; align-items: center; justify-content: center; color: #14213d; font-weight: bold;">S</div>
         <div style="flex: 1;"><b>Stackademy v1.0.0</b><br><span style="color: #fca311; font-size: 12px;">openai gpt-6-luna</span></div>
         <span style="color: #fca311;">&#x2b6f;</span>
       </div>
       <div style="padding: 12px; background: repeating-linear-gradient(45deg, #f4f4f4, #f4f4f4 10px, #ebebeb 10px, #ebebeb 20px);">
         <div style="display: flex; gap: 8px; align-items: flex-end; margin-bottom: 10px;">
           <div style="width: 28px; height: 28px; border-radius: 50%; background: #fca311; flex: none;"></div>
           <div style="background: #e5e5e5; color: #14213d; padding: 8px 10px; border-radius: 0 12px 12px 12px; max-width: 75%;">Welcome to Stackademy! How can I help you today?</div>
         </div>
         <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
           <div style="background: #fca311; color: #14213d; padding: 8px 10px; border-radius: 12px 12px 0 12px; max-width: 75%;">Do you offer any courses on AI?</div>
         </div>
         <div style="color: #fca311; font-size: 12px;">&#8226;&#8226;&#8226; Stanley is typing</div>
       </div>
       <div style="display: flex; gap: 8px; align-items: center; padding: 8px; border-top: 1px solid #d1dbe3; background: #fff;">
         <div style="flex: 1; background: #f1f1f1; color: #6c757d; border-radius: 12px; padding: 8px 10px;">Ask me anything about Stackademy courses...</div>
         <span style="color: #fca311; font-size: 18px;">&#10148;</span>
       </div>
     </div>
     <div style="display: grid; grid-template-columns: auto 1fr; gap: 4px 10px; margin-top: 10px; font-size: 13px;">
       <code>mainContainer</code><span>the frame around everything</span>
       <code>conversationHeader</code><span>the dark bar at the top, with <code>appLogoUrl</code> in its circle</span>
       <code>messageList</code><span>the striped area that holds the conversation, and <code>appBackgroundImageUrl</code></span>
       <code>incomingMessage</code><span>the assistant's gray bubble, with <code>assistantAvatarUrl</code> beside it</span>
       <code>outgoingMessage</code><span>the user's amber bubble, with <code>userAvatarUrl</code> beside it</span>
       <code>typingIndicator</code><span>"Stanley is typing", while the LLM answers</span>
       <code>messageInput</code><span>the box at the bottom, where the user types</span>
       <code>buttons</code><span>the send arrow, the attach button, and the header's buttons</span>
     </div>
   </div>


A Two-Minute CSS Crash Course
-----------------------------

Styles are written as *CSS values*, the same values that every web page uses. You only need four kinds.

Colors
~~~~~~

There are three ways to write a color. Use whichever your brand guide gives you.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Kind
     - Example
     - Notes
   * - Hex code
     - ``"#fca311"``
     - The most common. A ``#`` and six digits or letters (0-9, a-f): two each for red, green and
       blue. ``"#ffffff"`` is white, ``"#000000"`` is black. Short forms like ``"#fff"`` work too.
       **Put hex colors in quotes**, because in YAML a ``#`` starts a comment.
   * - Color name
     - ``tomato``
     - Browsers know about 140 color names, such as ``navy``, ``gold``, ``white`` and ``tomato``. See
       `the list of names <https://developer.mozilla.org/en-US/docs/Web/CSS/named-color>`__.
   * - ``rgb`` / ``rgba``
     - ``rgba(255, 255, 255, 0.8)``
     - Red, green and blue from 0 to 255. The ``a`` version adds *opacity* from 0 (invisible) to 1
       (solid), so ``0.8`` is 80% solid, and lets what's behind it show through a little.
       ``hsl()`` and ``hsla()`` colors work too.

Any color picker shows a color's hex code. Try `Google's color picker
<https://www.google.com/search?q=color+picker>`__, or your design tool's.

Sizes
~~~~~

A size is a number and a unit, with no space between them:

- ``px`` (pixels) is a fixed size: ``16px`` is a typical text size.
- ``em`` and ``rem`` are relative to the text size: ``1em`` is one text-height, ``0.5em`` half of one.
  Sizes in ``em`` grow and shrink with the text.
- ``0`` needs no unit.

Fonts
~~~~~

A *font stack* is a list of fonts, separated by commas. The visitor's browser uses the first one that it
has, so a stack ends with a generic family: ``sans-serif``, ``serif`` or ``monospace``.

.. code-block:: yaml

   fontFamily: '"Georgia", "Times New Roman", serif'

Most visitors don't have your brand font installed, so the chat can download one for them, from the free
`Google Fonts <https://fonts.google.com>`__ catalog. Find a font there, and copy its name exactly:

.. code-block:: yaml

   googleFont: Nunito

That's all: when ``fontFamily`` isn't set, the chat uses the Google font, with a sensible stack behind it.

Images
~~~~~~

An image is a web address (url) that starts with ``https://`` and ends at the image itself, usually
``.png``, ``.jpg``, ``.svg`` or ``.webp``. Paste it into a browser's address bar: if you see the image and
nothing else, it's the right url. A link to a page that *shows* the image, such as a Google Drive or
Dropbox sharing page, won't work. Host images somewhere public, such as your website, a CDN, or a public
bucket.

- **Logo and avatars** are shown in small circles, about 42 pixels wide. Use a square image, at least 128
  by 128 pixels, with its subject in the middle. A logo is fitted whole into a white circle. An avatar
  fills its circle, so its corners are cut off.
- **Background images** sit behind the conversation. Choose a quiet image or a light pattern, so that the
  messages stay easy to read, and keep it under about 500 KB, so that the chat loads quickly.

When you apply the manifest, Smarter opens each image url, as a browser would, and refuses the manifest
if one doesn't answer with an image: a typo, an image that hasn't been uploaded yet, a private file, or a
link to a web page instead of the image itself. A url that forwards to the image (a redirect) is fine.

If an image disappears later, after it was applied, the chat leaves it out rather than show a broken
picture. It just won't show your image.


Every Setting
-------------

All settings are optional.

The overall look
~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 28 47 25

   * - Setting
     - What it does
     - Example
   * - ``appLogoUrl``
     - Your logo, in a circle at the left of the header. It's also shown on the LLMClient's card in
       the web console.
     - ``https://cdn.example.com/logo.png``
   * - ``appBackgroundImageUrl``
     - A picture behind the conversation. See `Background Images`_.
     - ``https://cdn.example.com/bg.png``
   * - ``appBackgroundImageSize``
     - How the picture fills the area: ``cover`` (the default) fills it and crops the picture's edges,
       ``contain`` shows the whole picture, and ``auto`` repeats it at its own size, like tiles. Use
       ``auto`` for a pattern.
     - ``auto``
   * - ``assistantAvatarUrl``
     - A small picture beside each of the assistant's messages: a mascot, a face, or your logo.
     - ``https://cdn.example.com/stanley.png``
   * - ``userAvatarUrl``
     - A small picture beside each of the user's messages.
     - ``https://cdn.example.com/user.png``
   * - ``googleFont``
     - A font from `Google Fonts <https://fonts.google.com>`__, which the chat downloads.
     - ``Nunito``
   * - ``fontFamily``
     - The chat's font stack. It wins over ``googleFont``, so use it to put a Google font in a stack of
       your own.
     - ``'"Nunito", Arial, sans-serif'``
   * - ``fontSize``
     - The size of the chat's text. Every other size grows and shrinks with it. The default is ``16px``.
     - ``15px``
   * - ``borderRadius``
     - How round the corners of the message bubbles and of the message box are. ``0`` is square, and the
       default is ``0.7em``.
     - ``16px``

The parts of the chat
~~~~~~~~~~~~~~~~~~~~~

Each part is a section of ``styles``, with its settings indented beneath it:

.. code-block:: yaml

   styles:
     conversationHeader:
       backgroundColor: "#14213d"
       color: "#ffffff"

.. list-table::
   :header-rows: 1
   :widths: 24 30 46

   * - Section
     - Settings
     - What they color
   * - ``mainContainer``
     - ``backgroundColor``, ``color``, ``borderColor``
     - The frame around the whole chat, its default text color, and the thin line around it.
   * - ``conversationHeader``
     - ``backgroundColor``, ``color``, ``infoColor``, ``borderColor``
     - The bar at the top: its background, the LLMClient's name (``color``), the line beneath the name,
       which names the LLM provider and model (``infoColor``), and the line under the bar.
   * - ``messageList``
     - ``backgroundColor``, ``color``
     - The area that holds the conversation. Over a background image, ``backgroundColor`` tints the
       image. See `Background Images`_.
   * - ``incomingMessage``
     - ``backgroundColor``, ``color``, ``borderColor``, ``linkColor``
     - The assistant's bubbles: their color, their text, an optional thin line around them, and the
       links in them.
   * - ``outgoingMessage``
     - ``backgroundColor``, ``color``, ``borderColor``, ``linkColor``
     - The user's bubbles, likewise.
   * - ``messageInput``
     - ``backgroundColor``, ``editorBackgroundColor``, ``color``, ``placeholderColor``, ``borderColor``
     - The strip at the bottom (``backgroundColor``), the box itself (``editorBackgroundColor``), what the
       user types (``color``), the hint in the empty box (``placeholderColor``, whose words are
       ``spec.config.prompt.appPlaceholder``), and the line above the strip.
   * - ``buttons``
     - ``color``
     - The send and attach buttons, and the header's buttons.
   * - ``typingIndicator``
     - ``color``
     - "Stanley is typing" and its bouncing dots.


Background Images
-----------------

A background image sits behind the conversation, and ``messageList.backgroundColor`` is laid over it like
tinted glass. A solid color would hide the image completely, so use an ``rgba`` color with an opacity
below 1:

.. code-block:: yaml

   styles:
     appBackgroundImageUrl: https://cdn.example.com/stackademy/pattern.png
     appBackgroundImageSize: auto              # a pattern, repeated like tiles
     messageList:
       backgroundColor: rgba(255, 255, 255, 0.85)   # 85% white, over the pattern

The higher the opacity, the fainter the image, and the easier the messages are to read. Between ``0.75``
and ``0.9`` usually looks good. For a dark chat, tint with a dark color instead, such as
``rgba(20, 33, 61, 0.9)``.


Case Study: Stackademy
----------------------

Stackademy is an online coding school, the fictional company behind several of Smarter's examples. Its
course advisor, an LLMClient named ``stackademy_sql``, answers questions about the course catalog. It works
well, but on Stackademy's website it looks like every other chat. The marketing team sends over the brand
guide:

- **Colors:** Oxford navy ``#14213d``, amber ``#fca311``, platinum gray ``#e5e5e5``, and white.
- **Font:** Nunito, a rounded, friendly sans-serif.
- **Logo:** a square PNG, and a mascot, *Stanley*, the friendly owl who answers students' questions.
- **Tone:** welcoming, a little playful, never childish.

Here's how a prompt engineer turns that into ``styles``, one step at a time, applying the manifest after
each step and reloading the workbench to see the result.

Step 1: put the images online
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The logo, Stanley's portrait and a faint pattern of code symbols go on Stackademy's CDN. Each is checked
by pasting its url into a browser.

Step 2: the header and the logo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The header is the first thing that visitors see, so it gets the boldest color: navy, with white text,
and the model's name in amber.

.. code-block:: yaml

   styles:
     appLogoUrl: https://cdn.stackademy.edu/brand/logo.png
     conversationHeader:
       backgroundColor: "#14213d"
       color: "#ffffff"
       infoColor: "#fca311"

Step 3: the bubbles
~~~~~~~~~~~~~~~~~~~

Students' own messages are amber, and Stanley's are platinum gray, both with navy text. Navy on amber is
easy to read; white on amber, the first idea, was too faint. Links in Stanley's answers are a clear
blue, and Stanley's portrait goes beside them.

.. code-block:: yaml

     assistantAvatarUrl: https://cdn.stackademy.edu/brand/stanley.png
     incomingMessage:
       backgroundColor: "#e5e5e5"
       color: "#14213d"
       linkColor: "#0b57d0"
     outgoingMessage:
       backgroundColor: "#fca311"
       color: "#14213d"

Step 4: the font, the corners, and the background
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Nunito comes from Google Fonts. Rounder corners suit its friendly letters. The code-symbol pattern is
tiled behind the conversation, and tinted 85% white so that it whispers rather than shouts.

.. code-block:: yaml

     googleFont: Nunito
     fontSize: 15px
     borderRadius: 16px
     appBackgroundImageUrl: https://cdn.stackademy.edu/brand/pattern.png
     appBackgroundImageSize: auto
     messageList:
       backgroundColor: rgba(255, 255, 255, 0.85)
       color: "#14213d"

Step 5: the finishing touches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The send button and the typing indicator pick up the amber, and the message box is a soft gray, so that
it reads as a place to type.

.. code-block:: yaml

     messageInput:
       editorBackgroundColor: "#f1f1f1"
       placeholderColor: "#6c757d"
     buttons:
       color: "#fca311"
     typingIndicator:
       color: "#fca311"

Step 6: check, and ship
~~~~~~~~~~~~~~~~~~~~~~~

Before deploying, the prompt engineer checks three things:

1. **Can everyone read it?** Each text color is checked against its background with WebAIM's free
   `contrast checker <https://webaim.org/resources/contrastchecker/>`__. Aim for its "WCAG AA: Pass".
2. **Does it work on a phone?** The workbench is resized to a phone's width.
3. **Does it survive a long answer?** A question that produces a table, a code block and a list.

Then the LLMClient is deployed, and the very same look appears on Stackademy's website, which embeds it
with Smarter Chat. No web developer was needed: the next time marketing changes a color, the prompt
engineer changes one line and applies the manifest again.

The complete manifest is one of Smarter's built-in examples. In it, Stackademy's images are on Smarter's
own CDN, rather than Stackademy's:

.. literalinclude:: ../../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-llmclient-sql.yaml
   :language: yaml
   :caption: stackademy-llmclient-sql.yaml


More Examples
-------------

Every built-in LLMClient has styles, from a single color to a full theme, so each is an example to copy.
They're in the Smarter repository, under
`smarter/smarter/apps/llmclient/data/llm-clients/
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmclient/data/llm-clients>`__:

- ``llmclient-simple.yaml``: just a logo and one color. A little goes a long way.
- ``llmclient-mcp-builder.yaml``: a dark theme, like a code editor's, in a monospace font.
- ``llmclient-math.yaml``: a chalkboard, with a handwriting font and a wooden frame.
- ``llmclient-weather.yaml``: a sunny sky, with round, puffy bubbles.
- ``llmclient-research-analyst.yaml``: a library's reading room, in a serif font.
- ``llmclient-smarter.yaml``: Smarter's own orange and gold.


Troubleshooting
---------------

**Apply says a value "is not valid".** The error names the setting and shows the value. Check its form
against `A Two-Minute CSS Crash Course`_: a color needs its ``#``, a size needs its unit (``16px``, not
``16``), and an image url must start with ``https://`` (not ``http://``).

**Apply says an image "is not available".** Smarter couldn't open the image. Paste the url into a
private browser window: if you don't see the image, nobody else will either. ``HTTP 403`` or ``HTTP 404``
usually means a typo, or a file that isn't uploaded or isn't public yet.

**Apply says an image is "a text/html page, not an image".** The url is of a page that *shows* the image,
such as a sharing link. Right-click the image, choose *Copy Image Address*, and use that url.

**Apply says the manifest "has keys that it does not define".** A setting's name is misspelled, or is in
the wrong section. Names are case-sensitive: ``backgroundColor``, not ``backgroundcolor`` or
``background_color``.

**Apply says that spec.config "is split into prompt ... and styles".** The manifest was written before
``spec.config`` had its ``prompt`` and ``styles`` sections. Indent its settings under ``prompt:``, and move
``appLogoUrl`` and ``appBackgroundImageUrl`` to ``styles:``, as the error lists.

**A hex color disappeared.** In YAML, ``#`` starts a comment, so ``backgroundColor: #fca311`` is an empty
setting. Quote it: ``backgroundColor: "#fca311"``.

**The font didn't change.** Check the name's spelling against `Google Fonts <https://fonts.google.com>`__,
including its capitals and spaces (``Source Sans 3``). If you also set ``fontFamily``, it wins.

**The background image doesn't show.** ``messageList.backgroundColor`` may be solid. Give it an opacity
below 1, such as ``rgba(255, 255, 255, 0.85)``.

**The logo or avatar doesn't show.** The image was available when you applied the manifest, but isn't
now. Paste its url into a browser to check it.


Under the Hood
--------------

This section is for the curious, and for web developers.

Smarter Chat is built on chatscope's open source chat components,
`@chatscope/chat-ui-kit-react <https://github.com/chatscope/chat-ui-kit-react>`__, and their theme,
`@chatscope/chat-ui-kit-styles <https://github.com/chatscope/chat-ui-kit-styles>`__. ``styles`` follows
the theme's design closely: its sections are chatscope's components (``MainContainer``,
``ConversationHeader``, ``MessageList``, ``Message``, ``MessageInput``, ``Button``, ``TypingIndicator`` and
``Avatar``), and each setting is one of the theme's variables, such as ``$conversation-header-bg-color``
for ``conversationHeader.backgroundColor``. Each setting's description in the
:doc:`Pydantic models <sam/models>` names its variable.

chatscope's theme is compiled ahead of time, so Smarter Chat can't recompile it for each LLMClient.
Instead, the config api returns the styles (with snake_case keys, as ``llmclient.styles``), and the chat
sets each one as a CSS custom property on its root element, ``.SmarterChat``. Its stylesheet applies
the properties to chatscope's elements, with chatscope's own value as each one's fallback:

.. code-block:: css

   .SmarterChat .cs-conversation-header {
     background-color: var(--smarter-chat-header-bg, #f6fbff);
   }

The properties are named ``--smarter-chat-<part>-<setting>``, for example ``--smarter-chat-header-bg``,
``--smarter-chat-incoming-link-color`` and ``--smarter-chat-input-placeholder-color``, plus
``--smarter-chat-font-family``, ``--smarter-chat-font-size`` and ``--smarter-chat-border-radius``. A page
that embeds the chat can set them itself, on ``.SmarterChat`` in its own stylesheet, and anything beyond
them can be styled with chatscope's ``cs-`` classes, and Smarter Chat's ``smarter-chat-`` classes.

Because styles are written into every page that embeds the LLMClient, Smarter accepts only plain values:
colors, sizes and font names that can't contain anything else, and ``https`` image urls. Apply rejects
any other value, and the chat ignores one that it receives. Apply also requests each image url, with
the same protections as plugins' web requests (public addresses only, validated redirects, timeouts),
and requires HTTP 200 and a Content-Type that isn't a web page.
