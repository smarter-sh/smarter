Terminal Emulator React Component
===================================

The Terminal Emulator React component brings real-time log streaming directly
into your browser, leveraging Django 6.x’s ASGI technology and modern web streams
for instant, interactive feedback. Log streams are customized for user context,
providing a personalized view of relevant log streams based on the user’s role
and permissions. With a sleek, responsive design, this component faithfully recreates
the look and feel of a classic terminal using xterm.js, automatically updating as new log entries
arrive from the backend. Log entries follow Smarter’s strict formatting
style guide, clearly identifying the full Python path, class, and method where
each entry originates — making Smarter log streams an unparalleled forensic resource
for understanding complex prompting interactions and AI behavior. JSON output
is not only well-formatted but also colorized for enhanced readability, ensuring
that both structured and plain-text logs are easy to scan and understand. This
component is ideal for monitoring, debugging, and teaching, providing a
seamless, visually rich terminal experience within any web application.

.. toctree::
   :maxdepth: 1
   :caption: Terminal Emulator React Component

   ../lib/logging/redis-log-handler
   ../lib/logging/waffle-switched-logging
   ../dashboard/views/logs/reactapp
   ../dashboard/views/logs/urls
   ../dashboard/views/logs/api



.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/terminal-emulator-react-component.png
   :alt: Terminal Emulator React Component Screenshot
   :class: screenshot
   :align: center
   :width: 80%

Component Usage Example
------------------------

.. literalinclude:: ../../../../smarter/react/terminal_emulator/src/components/Terminal/Component.stories.tsx
   :language: tsx


Core Terminal Component
------------------------

.. literalinclude:: ../../../../smarter/react/terminal_emulator/src/components/Terminal/Component.tsx
   :language: tsx
   :start-after: "interface TerminalEmulatorProps"
   :end-before: "export function"
