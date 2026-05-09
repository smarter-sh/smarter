Prompt List React Component
===================================

The Prompt List React component offers users a flexible and interactive way to
browse, view, and manage available chatbots or prompts. By fetching data
directly from a live API, it ensures that the list is always up-to-date, and
provides intuitive controls for toggling between list and thumbnail views. With
built-in error handling and responsive design, this component delivers a seamless
experience for exploring both personal and shared chatbots made possible via
Smarter's role-based access control, which makes it easy to find and interact
with the resources you need—all without requiring a page reload or manual refresh.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/prompt-list-react-component.png
   :alt: Prompts Passthrough React Component Screenshot
   :class: screenshot
   :align: center
   :width: 80%

Component Usage Example
------------------------

.. literalinclude:: ../../../../smarter/react/prompt_list/src/components/Prompts/Component.stories.tsx
   :language: tsx


Core Prompts Component
-----------------------

.. literalinclude:: ../../../../smarter/react/prompt_list/src/components/Prompts/Component.tsx
   :language: tsx
   :start-after: "interface PromptListProps"
   :end-before: "export function"
