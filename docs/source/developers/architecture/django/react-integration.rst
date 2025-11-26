Django-React Integration
========================

There are several considerations for getting React to work inside a
Django project. React’s native build tools assume that you’re building a
standalone web app as opposed to more of a drop-in page component in our
case. Additionally, Django does opinionated things with your project’s
static assets like for example, the css/js bundles that React’s build
tools create.

React App Configuration
-----------------------

We leverage Django REST Framework to implement a /config api end point
for all chatbots that returns a json dict with the React app
configuration settings. This endpoint accepts ``POST`` requests, and it
is referenced directly from inside of the React app at startup. The json
dict that it returns is distributed throughout the React app as
``props.config``.

example url: https://platform.smarter.sh/chatapp/example/config/

See this complete `example config <./json/reactapp.config.json>`__ json
dict, based on the following overall structure:

.. code:: json

   {
     "session_key": "433f830c189d83f <-- 64-character hashed key string --> f9c95d17ae5b07c",
     "sandbox_mode": true,
     "debug_mode": true,
     "chatbot": {
       "account": {},
       "name": "example",
       "app_name": "Smarter Demo",
       "app_assistant": "Lawrence",
       "app_welcome_message": "Welcome to the Smarter demo!",
       "app_example_prompts": [
         "What is the weather in San Francisco?",
         "What is an Everlasting Gobstopper?",
         "example function calling configuration"
       ],
       "app_placeholder": "Ask me anything...",
       "url": "http://example.3141-5926-5359.api.localhost:8000/",
       "url_chatbot": "http://example.3141-5926-5359.api.localhost:8000/chatbot/",
       "url_chatapp": "http://example.3141-5926-5359.api.localhost:8000/chatapp/"
     },
     "meta_data": {},
     "history": [],
     "tool_calls": [],
     "plugins": {
       "meta_data": {
         "total_plugins": 2,
         "plugins_returned": 2
       },
       "plugins": []
     }
   }

React App Setup
---------------

- **placement within folder structure.** The React app was scaffolded
  with ViteJS and is added to the Django app
  `chatapp <./smarter/smarter/apps/chatapp/reactapp/>`__.

- **vite.config.ts.** Note that a.) Django’s collectstatic procedure
  must be able to discover the existence of React builds, and that b.)
  The url scheme in the React-generated templates need to account for
  how Django serves static assets in both dev and production
  environments. We leverage the
  `vite.config.ts <../smarter/smarter/apps/chatapp/reactapp/vite.config.ts>`__
  resource to prefix all paths with whatever path we’ve decided in
  Django settings for serving static assets. More on this, and a code
  sample, below.

  .. code:: javascript

     export default defineConfig({
       plugins: [react()],
       base: "/static/",
       build: {
         sourcemap: true,
       },
     });```

- **index.html.** The original
  `index.html <./smarter/smarter/apps/chatapp/reactapp/index.html>`__
  created by Vite is completely replaced by a django template that a.)
  inherits our custom base.html template, b.) contains Django template
  blocks to ensure correct placement of React’s elements within the DOM.
  More on this, and a code sample, below.

  .. code:: django

     {% extends "base.html" %}

     {% block content %}
     {% endblock %}

     {% block dashboard_content %}
       {{ block.super }}
       <div id="smarter_chatapp_root"></div>
     {% endblock %}

     {% block react_javascript %}
       {{ block.super }}
       {{ react_config|json_script:'react-config' }}
     {% endblock %}

Django Template Engine Configuration
------------------------------------

The Django template engine needs to know how to find React-rendered html
templates. Note that React’s builds are generated in a subfolder named
``dist`` located in the root folder of the React project, and that it’s
``index.html`` entry point file contains links to auto-generated css and
js bundles, meaning that the rendered index.html is specific to the
resources in the build that generated it, and it therefore cannot be
generalized/templated. Thus, we need a way to gracefully enable Django’s
templating engine to ‘discover’ these apps in whichever Django apps they
might exist, so that these files can be served by Django templates
as-is. To this end we’ve created a custom React `template
loader <./smarter/smarter/template_loader.py>`__ and a 2nd template
engine located in `base.py <./smarter/smarter/settings/base.py>`__ that
references the custom loader. We additionally created this custom `base
template <./smarter/smarter/templates//chatapp/base_react.html>`__ for
React that ensures that React’s ``<div id="root"></div>`` DOM element
and it’s js entry point bundle are correctly placed with the DOM.

.. code:: python

   class ReactAppLoader(FilesystemLoader):
       """A custom template loader that includes each django app's reactapp/dist directory in the search path."""

       def get_dirs(self):

           # checks every Django app for a subfolder named 'reactapp/dist/'
           dirs = super().get_dirs()
           for app in apps.get_app_configs():
               dirs.append(os.path.join(app.path, "reactapp", "dist"))
           return dirs

.. code:: python

     {
         # our custom template engined is named 'react'
         "NAME": "react",
         "BACKEND": "django.template.backends.django.DjangoTemplates",
         # it must be explicitly instructed to check the project
         # template folder
         "DIRS": [
             BASE_DIR / "templates",
         ],
         "APP_DIRS": False,
         "OPTIONS": {
             "loaders": [
                 # our custom template loader goes here...
                 "smarter.apps.common.template_loader.ReactAppLoader",
                 "django.template.loaders.filesystem.Loader",
             ],
             "context_processors": [
                 #
                 # other context processors ...
                 #
                 "django.template.context_processors.request",
                 #
                 # other context processors ...
                 #
             ],
         },
     },

React index.html template
~~~~~~~~~~~~~~~~~~~~~~~~~

The original ``index.html`` created by Vite is replaced with this Django
template. Note that this template is first processed by React’s build
process, which will convert the ``main.jsx`` reference to an actual js
bundle filename. And then afterwards, Django’s collectstatic procedure
will copy the ``dist`` folder contents to the staticfiles folder, to be
served by Django’s static asset server.

chatapp/base_react.html:

.. code:: django

   {% extends "smarter/base.html" %}

   {% block content %}
   {% endblock %}

   {% block dashboard_content %}
     {{ block.super }}
     <div id="smarter_chatapp_root"></div>
   {% endblock %}

   {% block react_javascript %}
     {{ block.super }}
     {{ react_config|json_script:'react-config' }}
   {% endblock %}

Example Django view template for serving a React app:

.. code:: django

   {% extends "chatapp/base_react.html" %}

   {% block canonical %}
   <link rel="canonical" href="/chatapp/" />
   {% endblock %}

   {% block react_javascript %}
     {{ block.super }}
     <script type="module" src="/src/main.jsx"></script>
   {% endblock %}

Django TEMPLATES settings
~~~~~~~~~~~~~~~~~~~~~~~~~

We created this second template engine that is customized for React.

.. code:: python

     {
         "NAME": "react",
         "BACKEND": "django.template.backends.django.DjangoTemplates",
         "DIRS": [
             BASE_DIR / "templates",
         ],
         "APP_DIRS": False,
         "OPTIONS": {
             "loaders": [
                 "smarter.apps.common.template_loader.ReactAppLoader",
                 "django.template.loaders.filesystem.Loader",
             ],
             "context_processors": [
                 #
                 # other context processors ...
                 #
                 "django.template.context_processors.request",
                 #
                 # other context processors ...
                 #
             ],
         },
     },

Django Static Asset Collection & Serving
----------------------------------------

vite.config.ts
~~~~~~~~~~~~~~

Vite is highly configurable, and it greatly simplifies systematically
making the kinds of minor adjustments needed to get the React app
working inside a Django-managed web page. Note the addition of the
``/static/`` prefix to all urls that vite generates which, conveniently,
are limited to static assets like images, css, and js.

.. code:: javascript

   export default defineConfig({
     plugins: [react()],
     base: "/static/",
     build: {
       sourcemap: true,
     },
   });

CORS Configuration
------------------

In dev we have to deal with CORS because, for development purposes,
React is served from a different port, http://localhost:5173/, than
Django is, http://127.0.0.1:8000/.

The following additional settings are necessary for the local dev
environment:

.. code:: python

   INSTALLED_APPS += [
       "corsheaders",
   ]
   MIDDLEWARE += [
       "corsheaders.middleware.CorsMiddleware",
       "django.middleware.common.CommonMiddleware",
   ]

   CORS_ALLOWED_ORIGINS = [
       "http://localhost:5173",
   ]

   # for any React-based implementations of plugin technologies
   # like say, Wordpress, Drupal, salesforce, etc.
   CORS_ALLOW_HEADERS = list(default_headers) + [
       "x-api-key",
   ]

Authentication & CSRF
---------------------

Web-based session authentication managed by Django, which is nice as
it’s one less thing we have to worry about in React. However, in doing
so we oblige ourselves to additionally working with Django’s built-in
protections against Cross-Site Request Forgery (CSRF), which is
cookie-based. Django’s default name for the cookie it creates is,
“csrftoken”.

.. code:: javascript

   const csrftoken = getCookie("csrftoken");
   const headers = {
     "X-CSRFToken": csrftoken, // <---- add this to all request headers
   };

So, for example, suppose that you have a Django template that includes a
form. The server-side and client-side code, respectively, would look
like the following:

Django template:

.. code:: django

   <form>
     {% csrf_token %}
     <input type="text" placeholder="Type something..." name="my_input" />
     <button>Submit</button>
   </form>

JS event handler:

.. code:: javascript

     const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
     fetch('/', {
       method: 'POST',
       headers: {
         // other headers ...
         'X-CSRFToken': csrftoken
       },
       body: new FormData(form);
     })

Mixed Content Errors
--------------------

Be mindful that if the platform is deployed to Kubernetes then Django
will interpret it’s schema as ‘http’ rather than as ‘https’ due to the
fact that the pods are running behind a load balancer. To work around
this we created a custom Django parameter ``SMARTER_API_SCHEMA`` which
defaults to ‘http’ and is set to ‘https’ in production.
