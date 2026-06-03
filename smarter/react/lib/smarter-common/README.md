# Smarter Chatbots List app. React + TypeScript + Vite

This is the Smarter Common source code for React apps that are
part of the web console. It is a local package dependency of several
of the React apps used in the Smarter web console.

Contains the following:

- React Tabbed ListView that works with any Smarter resource (Plugin, Chatbot, etcetera)
- Django REST API integration functions

Downstream React apps install this package as
`npm install ../lib/smarter-common/dist`, leading to the
following dependency being created in package.json:

```json
  "dependencies": {
    "@smarter/common": "file:../lib/smarter-common/smarter-common-x.y.z.tgz",
    "react": "^19.2.5",
    "react-dom": "^19.2.5",
  },
```

## Production Build

The following creates a smarter-common-x.y.z.tgz distribution file in the root of
this repo. Be aware that .gitignore excludes *.tgz from git, thus, it is necessary
to have run this procedure at least once in development environments.

Optional 'clean slate' steps:

```console
unset NODE_ENV
npm config delete production
npm config delete omit
npm config get production
npm config get omit
rm -f package-lock.json
npm install
rm smarter-common*.tgz
```

To build and package for distribution

```console
rm -rf node_modules
npm ci --include=dev
npm run build
npm run pack:tgz
```

Be aware that this package has the following peer dependencies that require
occasional updates on major React releases:

```json
  "peerDependencies": {
    "react": "^19",
    "react-dom": "^19"
  },
```

## SessionContext

This is a common container that includes both a.) the information needed to
integration to Django, and b.) the

```typescript
import type { Plugin } from "@/lib/Types";
import ListView from "@/components/ListView"
import CardView from "@/components/CardView"
import type { SessionContext } from "@smarter/common";

const sessionContext: SessionContext = {
  ApiUrl,
  csrfCookieName,
  djangoSessionCookieName,
  cookieDomain,
  objectType: {} as Plugin,
  objectTypeName: "plugin",
  ListView: ListView,
  CardView: CardView,
};
```

## TabbedListView

```typescript
import { TabbedListView } from "@smarter/common";
import type { SessionContext } from "@smarter/common";
import type { Plugin } from "@/lib/Types";

function App({ sessionContext }: {sessionContext: SessionContext<Plugin>}) {
  return (
    <>
      <section className="mt-5 mb-5 container" id="plugin-list">
        <TabbedListView sessionContext={sessionContext} />
      </section>
    </>
  );
}
```
