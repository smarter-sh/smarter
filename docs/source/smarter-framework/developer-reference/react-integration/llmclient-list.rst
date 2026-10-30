LLMClient List React Component
===================================

The LLMClient List React component offers users a flexible and interactive way to
browse, view, and manage available llmclients or prompts. By fetching data
directly from a live API, it ensures that the list is always up-to-date, and
opens an llmclient's detail when one of its rows is chosen: its settings, its manifest, the
resources that it is built from, and those that use it (see
:doc:`../smarter-dashboard/resource_detail`). The
API pages and searches the llmclients, so the list shows one page at a time,
with previous and next page buttons and a page number box. Its search finds
matching llmclients on every page, not only the page shown, and clicking a column
header, such as Name or Provider, sorts all of them by that column (see
:doc:`../lib/django/pagination`). With
built-in error handling and responsive design, this component delivers a seamless
experience for exploring both personal and shared llmclients made possible via
Smarter's role-based access control, which makes it easy to find and interact
with the resources you need—all without requiring a page reload or manual refresh.

A list that you have seen before paints at once, from the browser's cache, while it asks the api
for a fresh page, and the api answers from its own cache: see :doc:`../lib/django/listview`.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/prompt-list-react-component.png
   :alt: Prompts Passthrough React Component Screenshot
   :class: screenshot
   :align: center
   :width: 100%

.. toctree::
   :maxdepth: 1
   :caption: LLMClient List Component Technical Reference

   llmclient-list/api
   llmclient-list/django-view
   llmclient-list/django-template
   llmclient-list/template-tags
   llmclient-list/index
