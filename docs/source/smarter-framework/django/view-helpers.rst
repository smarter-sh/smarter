View Helpers
====================

The Smarter View Helpers are a collection of Django view classes that provide
common functionality for web views in the Smarter application. These helpers
include features such as authentication, caching, as well as
HTML sanitizing, minimization, rendering and caching.

.. important::

   These view helpers are designed to be used as base classes for your own
   Django views. By inheriting from these helpers, you can more confidently
   implement common web view functionality without having to reinvent the wheel.


.. toctree::
   :maxdepth: 1

   view-helpers/smarter-view
   view-helpers/smarter-web-html-view
   view-helpers/smarter-web-never-cached
   view-helpers/smarter-web-authenticated
   view-helpers/smarter-authenticated-cached
   view-helpers/smarter-authenticated-never-cached
   view-helpers/smarter-admin-webview
