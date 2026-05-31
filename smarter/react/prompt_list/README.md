# Smarter Chatbots List app. React + TypeScript + Vite

This is the source code for the Terminal Emulator app located
at [http://localhost:9357/workbench/](http://localhost:9357/workbench/prompt_list/).

This component is served by Django in production. See:

- builds are distributed from s3://smarter.sh/react/prompt_list/ and gathered
  by Dockerfile during builds into Django's static asset folder.
- [smarter.apps.prompt.views.listview.view.PromptListView](../../smarter/apps/prompt/views/listview/view.py)
- [smarter.apps.prompt.templatetags.react_prompt_list.prompt_list_react_assets](../../smarter/apps/prompt/templatetags/react_prompt_list.py)
- [templates/react/prompt-list.html](../../smarter/templates/react/prompt-list.html)

## Setup

To run this component locally for development purposes:

```console
export NODE_ENV=dev
npm install
npm run build
npm run dev
```

For production builds:

```console
export NODE_ENV=production
npm install --include=dev
npm run build
npm run dev
```

To generate Storybooks:

```console
npx storybook@latest init
npm run build-storybook
npm run storybook
```

## Screen Shot

![Prompt List Screenshot](https://cdn.smarter.sh/github.com/smarter-sh/react/prompt-list-screenshot.png)

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
