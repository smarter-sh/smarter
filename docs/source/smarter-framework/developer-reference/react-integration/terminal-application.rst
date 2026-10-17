Terminal Emulator React Component
===================================

The Terminal Emulator React component brings a real bash shell, running inside the
platform's own server container, directly into your browser, leveraging Django 6.x's ASGI
technology, Django Channels and a WebSocket. With a sleek, responsive design, this component
faithfully recreates the look and feel of a classic terminal using xterm.js. The browser's
keystrokes and resizes go to a shell on a pseudo terminal in the server process, and the shell's
output comes back as raw bytes, so colors, job control and full screen programs work. When it
starts, it prints the pod that runs the shell, and how the session can end. This component is
ideal for teaching, demonstrating and debugging the platform from the inside. It is for
superusers only, and off unless ``SMARTER_ENABLE_WEB_CONSOLE_TERMINAL`` is set. See
:doc:`../../../smarter-platform/smarter-web-console`.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/terminal-emulator-react-component.png
   :alt: Terminal Emulator React Component Screenshot
   :class: screenshot
   :align: center
   :width: 100%


.. toctree::
   :maxdepth: 1
   :caption: Terminal Emulator Component Technical Reference

   terminal-application/api
   terminal-application/django-view
   terminal-application/django-template
   terminal-application/template-tags
   terminal-application/index
   terminal-application/example-usage
   terminal-application/react-component
