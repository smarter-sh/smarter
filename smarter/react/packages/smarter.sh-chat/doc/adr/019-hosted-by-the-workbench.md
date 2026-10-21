# ADR-019: The Workbench Hosts the Chat

## Status

Accepted

Amends [ADR-001](001-scope.md) and [ADR-002](002-three-builds.md): the developer Console, and the workbench app, are no
longer part of this package.

## Context

Smarter Chat was also the Smarter web console's prompt engineering workbench: its `App.tsx` rendered the chat with a
developer Console beside it, and its default build wrote that app into Django's static files. The Console's tabs
grew to include pages of the web console, the LLMClient's manifest editor and its deployment page, which the chat
could only display in iframes, with url checks, `X-Frame-Options` exceptions on the platform, and a `postMessage`
protocol between the frames. A change to the workbench was a change in two repositories, with a release between
them. And every user of the npm package downloaded a Console that only the workbench could display.

## Decision

The workbench is the platform's own React app, `@smarter/workbench`, in the platform's workspace. It imports
`SmarterChat` from this package, as any React application does, and puts its Console beside it, with the platform's
manifest editor and deployment page as components.

This package is the chat only. It has props for a page that hosts it: `verbose`, `reloadKey`, `headerActions`,
`onConfig`, `onNewChat` and `onModeChange`, and it exports `HeaderButton` for `headerActions`. `toggleMetadata`, the
Sandbox / Production mode switch, is an ordinary prop. The Console, its layout and its log viewer, the Docs
dialog, and the app build moved to the platform. `npm run build` builds the library and the embed script.

## Alternatives Considered

- **Keep the Console here, and add its new tabs as more iframes.** Each tab would add a page, a frame exception and a
  message type to the platform, for a feature that only the platform uses.
- **Export the Console's tabs from the platform to this package.** The platform's apps aren't published, and this
  package would depend on the platform's release cycle.

## Consequences

- **Positive:**
  - The package is smaller, and its api is a chat's: no prop or export that only the workbench can use.
  - The workbench imports its tabs directly: no iframes, frame exceptions or cross-frame messages.
  - A change to the workbench's Console is a change to the platform only.
  - The workbench uses the package as its other users do, so the props that a hosting page needs are tested by the
    platform's own use.
- **Negative:**
  - A change to what the chat tells its host is still a change in both repositories, with a release between them.
  - The platform's workspace builds this package's library before the workbench, its tests and its type check.
  - It was a breaking change: `Console`, `MenuItems`, `showConsole`, `logStreamUrl`, `manifestEditorUrl` and
    `deploymentUrl` were removed.

## Related ADRs

- [ADR-001: Scope: the Chat UI of Smarter LLMClients](001-scope.md)
- [ADR-002: One Source, Three Builds](002-three-builds.md)
- [ADR-014: Semantic Versioning and the Public Api](014-versioning.md)
