Prompt List React Component
===================================

The Prompt List React component offers users a flexible and interactive way to
browse, view, and manage available llmclients or prompts. By fetching data
directly from a live API, it ensures that the list is always up-to-date, and
provides intuitive controls for toggling between list and thumbnail views. The
API pages and searches the llmclients, so the list shows one page at a time,
with previous and next page buttons and a page number box, and its search finds
matching llmclients on every page, not only the page shown (see
:doc:`../lib/django/pagination`). With
built-in error handling and responsive design, this component delivers a seamless
experience for exploring both personal and shared llmclients made possible via
Smarter's role-based access control, which makes it easy to find and interact
with the resources you need—all without requiring a page reload or manual refresh.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/prompt-list-react-component.png
   :alt: Prompts Passthrough React Component Screenshot
   :class: screenshot
   :align: center
   :width: 100%

.. toctree::
   :maxdepth: 1
   :caption: Prompt List Component Technical Reference

   prompt-list/api
   prompt-list/django-view
   prompt-list/django-template
   prompt-list/template-tags
   prompt-list/index
