# Smarter Terminal Emulator app. React + TypeScript + Vite

This is the source code for the Terminal Emulator app located
at [http://localhost:9357/workbench/terminal_emulator/](http://localhost:9357/workbench/terminal_emulator/).

This component is served by Django in production. See:

- builds are distributed from s3://smarter.sh/react/terminal_emulator/ and gathered
by Dockerfile during builds into Django's static asset folder.
- [smarter.apps.prompt.views.listview.view.PromptListView](../../smarter/apps/prompt/views/listview/view.py)
- [smarter.apps.prompt.templatetags.react_prompt_list.prompt_list_react_assets](../../smarter/apps/prompt/templatetags/react_prompt_list.py)
- [templates/react/prompt-list.html](../../smarter/templates/react/prompt-list.html)

## Setup

### Running Locally

This configures Vite to serve the app locally, with console.debug() output enabled.
Run the app from from http://localhost:5173/. Note that Django also should be running
locally and be available at http://localhost:9357 in order for the React app to
be able to fetch from the Django API endpoints.

```console
export NODE_ENV=dev
npm install
npm run build
npm run dev
```

### Running Locally From Django

This configures Vite to generate a production React build, with the final build
bundle collected into Django's static asset folder. Run the Django web console
from http://localhost:9357/

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
trouble shooting purposes. http://example.com/static/react/prompt_passthrough/manifest.json

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
      "s3BucketPath": "s3://smarter.sh/react/prompt_passthrough/",
      "cloudfrontDistributionId": "E2NUOFBC8HY0W9"
    },
    "buildEnv": "production"
  }
}
```

### Generate Storybook

To generate Storybooks:

```console
npx storybook@latest init
npm run build-storybook
npm run storybook
```

## Screen Shot

![Server Logs Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/server-logs-screenshot.png)

## Vite Plugins

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on
dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the
configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
