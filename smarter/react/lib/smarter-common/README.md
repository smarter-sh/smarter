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

For production builds:

```console
export NODE_ENV=production
npm install --include=dev
npm run build
```
