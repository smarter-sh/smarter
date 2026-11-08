Dashboard React Component
===================================

The Dashboard React component provides a modern, interactive, and highly modular
interface for visualizing key resources, service health, instructor resources, tools,
and community contributions — all in one unified view. Unlike traditional Django
templates, which render static HTML on the server, this React-based dashboard
delivers a dynamic, real-time user experience with seamless updates and responsive
layouts. Its component-driven architecture makes it easy to extend, customize,
and integrate with APIs, while leveraging client-side rendering for snappy
performance and smooth interactivity. This approach empowers users with a richer,
more engaging dashboard that’s both flexible and future-proof compared to classic
server-rendered solutions.

Another key advantage of this dashboard is that each sub-component—such as
MyResources, ServiceHealth, BudgetAlerts, and others—connects to its own
dedicated API data source. This autonomy allows each widget to independently
manage when and how it fetches or refreshes its data, optimizing both
performance and user experience. For example, components can trigger updates
based on user actions, scheduled intervals, or even respond to real-time
asynchronous streams using technologies like ASGI. This decoupled approach
not only improves scalability and maintainability, but also enables advanced
features such as live updates and push notifications, which are difficult to
achieve with traditional server-rendered templates.

The dashboard is a page of the single-page console (:doc:`ADR-035 </adr/035-single-page-app>`), at
``/dashboard/``, the console's home. ``@smarter/console`` renders ``@smarter/dashboard``'s ``Dashboard``
component inside its frame, with the sidebar and the user menu, and builds its context from the console's
session: the cookies of its requests, and the urls of its widgets' endpoints in the console's dashboard api,
``/api/web/dashboard/``. The package has no build of its own; ``npm run dev`` in it renders the dashboard
from its example context, against the Django dev server's api. Django answers ``/dashboard/`` with the
console's page, and keeps the url name ``dashboard:dashboard``. See :doc:`../web-console-api`.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/dashboard-react-component.png
   :alt: Dashboard Passthrough React Component Screenshot
   :class: screenshot
   :align: center
   :width: 100%

.. toctree::
   :maxdepth: 1
   :caption: Dashboard Component Technical Reference

   dashboard/api
   dashboard/example-usage
   dashboard/react-component
