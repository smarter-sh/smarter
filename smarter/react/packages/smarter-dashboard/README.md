# Smarter Dashboard app. React + TypeScript + Vite

This is the source code for the Dashboard app located
at [http://localhost:9357/dashboard/](http://localhost:9357/dashboard/).

In the web console, `@smarter/console` imports this package (`src/index.ts`) and renders its `Dashboard`
at `/dashboard`, with a context built from the console's session (`src/lib/dashboard.ts` and
`src/routes/DashboardPage.tsx` there). The package has no build of its own: its `index.html` and
`src/main.tsx` are a development page only (`npm run dev`). Django answers the path with the console's
page, `smarter.apps.dashboard.views.console_app.ConsoleAppView` (ADR-035), and the widgets' data comes
from the dashboard api, `smarter.apps.dashboard.views.views.api`.

## Developer Setup and Guide

### Running Locally

This configures Vite to serve the app locally, with console.debug() output enabled.
Run the app from from http://localhost:5173/. Note that Django also should be running
locally and be available at http://localhost:9357 in order for the React app to
be able to fetch from the Django API endpoints.

```console
export NODE_ENV=development
npm install
npm run dev
```

### Running Locally From Django

This builds the console, which imports this package, and collects it into Django's
static asset folder. Run the Django web console from http://localhost:9357/

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

### Generate Storybook

To generate Storybooks:

```console
npx storybook@latest init
npm run build-storybook
npm run storybook
```

## Screen Shot

![Dashboard Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/smarter-dashboard-screenshot.png)

## Developer Notes

When running locally you should expect to see console error/warning messages
from the YouTube video player of the form

```console
Failed to execute 'postMessage' on 'DOMWindow': The target origin provided ('https://www.youtube.com') does not match the recipient window's origin ('http://localhost:9357').
```

These messages are benign and should be ignored.

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
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
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
        project: ["./tsconfig.node.json", "./tsconfig.app.json"],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from "eslint-plugin-react-x";
import reactDom from "eslint-plugin-react-dom";

export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs["recommended-typescript"],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.node.json", "./tsconfig.app.json"],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
]);
```
