# Smarter Chatbots List app. React + TypeScript + Vite

This is the Smarter Common source code for React apps that are
part of the web console. It is a local package dependency of several
of the React apps used in the Smarter web console.

Contains the following:

- React Tabbed ListView that works with any Smarter resource (Plugin, Chatbot, etcetera)
- Django REST API integration functions

## Setup

### Running Locally

```console
export NODE_ENV=development
npm install
npm run build
```

### Production Build

Downstream React apps install this package as
`npm install ../lib/smarter-common/dist`, leading to the
following dependency being created in package.json:

```json
  "dependencies": {
    "@smarter/common": "file:../lib/smarter-common/dist",
    "react": "^19.2.5",
    "react-dom": "^19.2.5",
  },
```

For production builds:

```console
export NODE_ENV=production
npm install --include=dev
npm run build
```

Be aware that this package has the following peer dependencies that might require
updating on major React releases:

```json
  "peerDependencies": {
    "react": "^19",
    "react-dom": "^19"
  },
```
