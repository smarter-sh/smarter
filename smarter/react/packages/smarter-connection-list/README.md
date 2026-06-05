# Smarter Connections List React App

This is the source code for the Connections List app located
at [http://localhost:9357/connection/](http://localhost:9357/connection/).

This component is served by Django. See also:

- [smarter.apps.connection.views.listview.view.ConnectionListView](../../smarter/apps/connection/views/listview/view.py)
- [smarter.apps.connection.templatetags.react_connection_list.connection_list_react_assets](../../smarter/apps/connection/templatetags/react_connection_list.py)
- [templates/react/connection-list.html](../../smarter/templates/react/connection-list.html)

## Screen Shot

![Connection List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/connection-list-screenshot.png)

## Setup

### Running Locally

This configures Vite to serve the app locally, with console.debug() output enabled.
Run the app from from [http://localhost:5173/](http://localhost:5173/). Note
that Django also should be running locally and be available at
[http://localhost:9357](http://localhost:9357) in order for the React app to
be able to fetch from the Django API endpoints.

```console
export NODE_ENV=development
npm install
npm run build
npm run dev
```

### Running Locally From Django

This configures Vite to generate a production React build, with the final build
bundle collected into Django's static asset folder. Run the Django web console
from [http://localhost:9357](http://localhost:9357)

```console
cd to/the/root/of/this/repo/

# Causes React to generate a production-optimized build.
export NODE_ENV=production

# builds ALL React apps, and also run Django static asset collection
make react-build

# Builds the Django Docker container.
make build

# Starts the Django app container
make run
```

### Production Build

For production builds:

```console
export NODE_ENV=production
npm install --include=dev
npm run build
npm run dev
```

The Smarter GitHub Action build workflow caches the React app build output to
speed up the build process in the expected case where React source code has
not changed.

Note that the manifest.json file includes meta data that can be used for
trouble shooting purposes.

Example: `http://example.com/static/react/smarter-connection-list/manifest.json`

```json
{
  "index.html": {
    "file": "assets/index-A7LvGMNl.js",
    "name": "index",
    "src": "index.html",
    "isEntry": true,
    "css": ["assets/index-B011HLqe.css"]
  },
  "_custom": {
    "buildTime": "2026-05-31T21:17:32.505Z",
    "version": "0.2.2",
    "config": {
      "cdnDeploy": false,
      "s3BucketPath": "s3://smarter.sh/react/smarter-connection-list/",
      "cloudfrontDistributionId": "E2NUOFBC8HY0W9"
    },
    "buildEnv": "production"
  }
}
```
