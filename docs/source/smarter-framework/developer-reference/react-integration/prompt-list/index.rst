Example index.html
====================


.. code-block:: html

  <!doctype html>
  <html lang="en">
    <head>
      <!--
       Everything that follows is for local development. These links
       ensure continuity between what you'll get when running the React app
       standalone in development mode versus running the same app inside
       the Django app (both local as well as production).
      -->
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>LLMClients List</title>

      <link rel="preconnect" href="https://fonts.googleapis.com">
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
      <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Inter:300,400,500,600,700" />

      <!--
       These assets originate from the Bootstrap premium theme used in web console.
      -->
      <link href="/assets/plugins/custom/fullcalendar/fullcalendar.bundle.css" rel="stylesheet" type="text/css" />
      <link href="/assets/plugins/custom/datatables/datatables.bundle.css" rel="stylesheet" type="text/css" />
      <link href="/assets/plugins/global/plugins.bundle.css" rel="stylesheet" type="text/css" />
      <link href="/assets/css/style.bundle.css" rel="stylesheet" type="text/css" />
      <link href="/common-styles.css" rel="stylesheet" type="text/css" />

      <!--
       These are ViteJS build assets
      -->
      <script type="module" crossorigin src="/static/react/prompt_list/assets/index.js"></script>
      <link rel="stylesheet" crossorigin href="/static/react/prompt_list/assets/index-wpawYy55.css">
    </head>
    <body>
      <!-- only used for development via 'npm run dev' -->
      <div
        id="smarter-prompt-list-root"
        django-csrf-cookie-name="csrftoken"
        django-session-cookie-name="sessionid"
        smarter-prompt-list-api-url="/prompt_list/logs/api/stream/"
        >
      </div>
    </body>
    <!--
      These assets originate from the Bootstrap premium theme used in web console.
    -->
    <script src="/assets/plugins/global/plugins.bundle.js"></script>
    <script src="/assets/js/scripts.bundle.js"></script>

  </html>
