# React Apps for the Smarter Web Console

This directory contains the React app npm workspace for the Smarter web console.

## Overview

The React frontend is organized as an npm workspace with standardized packages
under `packages/*`.

Key points:

- All package names are namespaced under `@smarter`.
- `@smarter/common` is the shared dependency package and must be built first.
- React app builds are managed with [Vite.js](https://vite.dev/).
- App structure, build behavior, and dependency patterns are
  standardized across packages.
- Build artifacts are written into Django static paths and then collected by Django.

## Build For Productino

Use the convenvience commands in Makefile to build all packages and integrate
to Django.

```console
make react-build
make collectstatic
make build
make run
```

## Workspace Layout

- Root workspace manifest: `smarter/react/package.json`
- Packages directory: `smarter/react/packages`
- Shared package: `smarter/react/packages/smarter-common`

Current app packages include:

- `smarter-authtoken-list`
- `smarter-connection-list`
- `smarter-dashboard`
- `smarter-plugin-list`
- `smarter-prompt-list`
- `smarter-prompt-passthrough`
- `smarter-provider-list`
- `smarter-secret-list`
- `smarter-terminal-emulator`
- `smarter-common`

## Workspace Build Orchestration

The workspace root uses npm workspaces and a build script that enforces build order:

```json
{
  "private": true,
  "workspaces": ["packages/*"],
  "scripts": {
    "build": "npm run build --workspace=@smarter/common && npm run build --workspaces --exclude=@smarter/common"
  }
}
```

Why this matters:

- `@smarter/common` is compiled first.
- All other packages that depend on `@smarter/common` build afterwards.
- This avoids dependency ordering issues and keeps builds deterministic.

## Standard Local Development Build Procedure

To build and run all React apps from the repository root,
run the following steps in order:

1. `make react-install`
    Creates shared `node_modules` for the React workspace.
2. `make react-build`
    Builds each React package and writes output into Django static path under `smarter/static/react`.
3. `make collectstatic`
    Consolidates static assets into Django `staticfiles`.
4. `make build`
    Builds the Docker container.
5. `make run`
    Starts the web console, typically served on localhost.

## Typical Package Pattern

A typical app package:

- Name format: `@smarter/<app-name>`
- Build stack: TypeScript + Vite
- Common dependency: `@smarter/common`
- Local commands usually include:
  - `dev`
  - `build`
  - `lint`
  - `preview`
  - `storybook`
  - `build-storybook`

Example package manifest reference: [packages/smarter-authtoken-list/package.json](./packages/smarter-authtoken-list/package.json)

## Vite and Django Integration

Each app uses a standardized Vite configuration to support Django integration
and deployment workflows.

Example vite config: [packages/smarter-authtoken-list/vite.config.ts](./packages/smarter-authtoken-list/vite.config.ts)

Common behavior includes:

- Output directory points to Django static React folder: [smarter/smarter/static/react/@smarter](../smarter/static/react/@smarter/)
- Build manifest is generated and used by Django template tags for hashed asset
  resolution.
- Custom metadata is injected into `manifest.json` after build.
- Optional post-build CDN deploy can sync to S3 and invalidate CloudFront when
  enabled in package config.
- Vite dev server proxies API and static routes to Django so app behavior in
  development is close to runtime behavior.
- Production builds remove `console.debug` via esbuild `pure` configuration.
- xterm-related dependencies may be chunked separately for better browser caching.

## Standardization Rules Across Apps

To keep all React apps consistent:

- Use `@smarter` namespace for package names.
- Depend on `@smarter/common` for shared functionality.
- Keep scripts and tooling aligned with the common pattern.
- Use Vite config conventions that target Django static integration.
- Preserve proxy behavior needed for local Django-backed development.
- Keep manifest behavior consistent so Django asset resolution remains reliable.

## Practical Notes

- If a package depends on `@smarter/common`, do not build it before common is built.
- If static assets appear stale in Django, re-run:
  1. `make react-build`
  2. `make collectstatic`
- For local feature work on a single package, use that package `dev` command, but
  follow the full build pipeline before integration testing through Django and Docker.
