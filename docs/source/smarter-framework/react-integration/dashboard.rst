Dashboard React Component
===================================

The Dashboard React component provides a modern, interactive, and highly modular
interface for visualizing key resources, service health, certifications, tools,
and community contributions — all in one unified view. Unlike traditional Django
templates, which render static HTML on the server, this React-based dashboard
delivers a dynamic, real-time user experience with seamless updates and responsive
layouts. Its component-driven architecture makes it easy to extend, customize,
and integrate with APIs, while leveraging client-side rendering for snappy
performance and smooth interactivity. This approach empowers users with a richer,
more engaging dashboard that’s both flexible and future-proof compared to classic
server-rendered solutions.

Another key advantage of this dashboard is that each sub-component—such as
MyResources, ServiceHealth, CertificateProgram, and others—connects to its own
dedicated API data source. This autonomy allows each widget to independently
manage when and how it fetches or refreshes its data, optimizing both
performance and user experience. For example, components can trigger updates
based on user actions, scheduled intervals, or even respond to real-time
asynchronous streams using technologies like ASGI. This decoupled approach
not only improves scalability and maintainability, but also enables advanced
features such as live updates and push notifications, which are difficult to
achieve with traditional server-rendered templates.

.. image:: https://cdn.smarter.sh/docs/smarter-framework/react-integration/dashboard-react-component.png
   :alt: Dashboard Passthrough React Component Screenshot
   :class: screenshot
   :align: center
   :width: 80%

Component Usage Example
------------------------

.. literalinclude:: ../../../../smarter/react/dashboard/src/components/Dashboard/Component.stories.tsx
   :language: tsx


Core Dashboard Component
--------------------------

.. literalinclude:: ../../../../smarter/react/dashboard/src/components/Dashboard/Component.tsx
   :language: tsx
   :start-after: "interface DashboardProps"
   :end-before: "export function"
