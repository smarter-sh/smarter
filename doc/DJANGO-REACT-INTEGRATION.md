# Django-React Integration

There are several considerations for getting React to work inside a Django project. Please note the following:

## React App Setup

- **placement within folder structure.** The React app was scaffolded with ViteJS and is added to the Django app [chatapp](./smarter/smarter/apps/chatapp/reactapp/).
- **vite.config.ts.** Note that a.) Django's collectstatic procedure must be able to discover the existence of React builds, and that b.) The url scheme in the React-generated templates need to account for how Django serves static assets in both dev and production environments. We leverage the [vite.config.ts](../smarter/smarter/apps/chatapp/reactapp/vite.config.ts) resource to prefix all paths with whatever path we've decided in Django settings for serving static assets. More on this, and a code sample, below.
- **index.html.** The original [index.html](./smarter/smarter/apps/chatapp/reactapp/index.html) created by Vite is completely replaced by a django template that a.) inherits our custom base_react.html template, b.) contains Django template blocks to ensure correct placement of React's elements within the DOM. More on this, and a code sample, below.

## Django Template Configuration

The Django template engine needs to know how to find React-rendered html templates. Note that React's builds are generated in a subfolder named `dist` located in the root folder of the React project, and that it's `index.html` entry point file contains links to auto-generated css and js bundles, meaning that the rendered index.html is specific to the resources in the build that generated it, and it therefore cannot be generalized/templated. Thus, we need a way to gracefully enable Django's templating engine to 'discover' these apps in whichever Django apps they might exist, so that these files can be served by Django templates as-is. To this end we've created a custom React [template loader](./smarter/smarter/template_loader.py) and a 2nd template engine located in [base.py](./smarter/smarter/settings/base.py) that references the custom loader. We additionally created this custom [base template](./smarter/smarter/templates//smarter/base_react.html) for React that ensures that React's `<div id="root"></div>` DOM element and it's js entry point bundle are correctly placed with the DOM.

### React index.html template

The original `index.html` created by Vite is replaced with this Django template. Note that this template is first processed by React's build process, which will convert the `main.jsx` reference to an actual js bundle filename. And then afterwards, Django's collectstatic procedure will copy the `dist` folder contents to the staticfiles folder, to be served by Django's static asset server.

smarter/base_react.html:

```django
{% extends "smarter/base.html" %}

{% block content %}
{% endblock %}

{% block react_content %}
  {{ block.super }}
  <div id="root"></div>
{% endblock %}

{% block react_javascript %}
  {{ block.super }}
  {{ react_config|json_script:'react-config' }}
{% endblock %}
```

Example Django view template for serving a React app:

```django
{% extends "smarter/base_react.html" %}

{% block canonical %}
<link rel="canonical" href="/chatapp/" />
{% endblock %}

{% block react_javascript %}
  {{ block.super }}
  <script type="module" src="/src/main.jsx"></script>
{% endblock %}
```

### Django TEMPLATES settings

We created this second template engine that is customized for React.

```python
  {
      "NAME": "react",
      "BACKEND": "django.template.backends.django.DjangoTemplates",
      "DIRS": [
          BASE_DIR / "templates",
      ],
      "APP_DIRS": False,
      "OPTIONS": {
          "loaders": [
              "smarter.template_loader.ReactAppLoader",
              "django.template.loaders.filesystem.Loader",
          ],
          "context_processors": [
              "smarter.apps.dashboard.context_processors.react",
              "django.template.context_processors.request",
              #
              # other context processors ...
              #
          ],
      },
  },
```

## Django Static Asset Collection & Serving

### vite.config.ts

Note the addition of `/static/`:

```javascript
export default defineConfig({
  plugins: [react()],
  base: "/static/",
  build: {
    sourcemap: true,
  },
});
```

## Backend integration via template context

The React app interacts with the backend via a REST API implemented with Django REST Framework. But we have to provide the app with the correct, environment-specific url for this API during app startup, along with other similar stateful data. We therefore need a way to pass a small set of data to React via the Django template which invokes it. We created a custom [Django template context](./smarter/smarter/apps/dashboard/context_processors.py) that generates this data, and a [Django base template](./smarter/smarter/templates/smarter/base_react.html) that converts it into a javascript element placed in the DOM, which is then [consumed by the React app](./smarter/smarter/apps/chatapp/reactapp/src/config.js) at startup as a const. Note that the custom React context processor is added to the custom React template engine, described above.

### Django context generation

```python
def react(request):
  """
  React context processor for all templates that render
  a React app.
  """
  base_url = f"{request.scheme}://{request.get_host}"
  return {
      "react": True,
      "react_config": {"BASE_URL": base_url, "API_URL": f"{base_url}/api/v0", "CHAT_ID": "SET-ME-PLEASE"},
  }
```

### Django base template setup

The Django templating code:

```django
{% block react_javascript %}
  {{ block.super }}
  {{ react_config|json_script:'react-config' }}
{% endblock %}
```

Which will render a DOM element like the following:

```html
<script id="react-config" type="application/json">
  {
    "BASE_URL": "http://127.0.0.1:8000",
    "API_URL": "http://127.0.0.1:8000/api/v0",
    "CHAT_ID": "SET-ME-PLEASE"
  }
</script>
```

### React app consumption

The DOM element can be consumed by JS/React like this:

```javascript
export const REACT_CONFIG = JSON.parse(
  document.getElementById("react-config").textContent,
);
```

## CORS Configuration

In dev we have to deal with CORS because, for development purposes, React is served from a different port, http://localhost:5173/, than Django is, http://127.0.0.1:8000/.

The following additional settings are necessary for the local dev environment:

```python
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
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-api-key",
]
```
