# @smarter.sh/ui-widgets

React widgets from the [Smarter](https://smarter.sh) web console's dashboard: the ones that show
no account data. The web console's dashboard uses them, and so does [smarter.sh](https://smarter.sh),
so that the two look the same.

| Widget            | What it shows                                                                     |
| ----------------- | --------------------------------------------------------------------------------- |
| `Cli`             | The Smarter command-line interface, as a terminal session                         |
| `Contribute`      | Ways to help the project, its repository's activity badges and contributing guide |
| `Extensions`      | Smarter Extensions: the official ones, a manifest that uses one, the registry     |
| `Instructors`     | The Instructor Guide and the Free Course Designs                                  |
| `Integrations`    | The Smarter Chat integrations: WordPress, Drupal, Shopify, Docusaurus, ...        |
| `McpServer`       | The Smarter Project MCP Server, with the command that adds it to Claude Code      |
| `Sdk`             | The Smarter SDKs, with their install commands, and links to the API reference     |
| `SelfHost`        | The path from a laptop to production: Docker Compose, the Helm chart, Terraform   |
| `VSCodeExtension` | The Smarter Manifest VS Code extension, with a mock editor                        |
| `WhatsNew`        | Notable features of recent Smarter releases                                       |

## Install

```console
npm install @smarter.sh/ui-widgets
```

React 19 is a peer dependency. Prereleases are published with the `alpha` and `beta` dist-tags,
e.g. `npm install @smarter.sh/ui-widgets@alpha`.

## Use

```jsx
import { SelfHost, Sdk } from "@smarter.sh/ui-widgets";

<div className="keen">
  <div className="row g-5 g-xl-10">
    <div className="col-xl-8">
      <SelfHost />
    </div>
    <Sdk openapiUrl="https://platform.smarter.sh/docs/openapi/" />
  </div>
</div>;
```

The library imports its own stylesheet, so a bundler such as Vite or webpack loads it along with
the widgets. A page without a bundler links `@smarter.sh/ui-widgets/style.css`.

### What the page provides

The widgets are styled for the [Keen](https://keenthemes.com/) Bootstrap theme, as the web console
is. This package doesn't include the theme. A page provides:

- **The Keen stylesheet.** The web console loads it on every page. A page with a design of its own,
  such as smarter.sh, can scope it to the elements that hold the widgets, as smarter.sh does with
  its `.keen` wrapper.
- **The Keen theme's images**, at their `/static/assets/media/` paths:
  - `illustrations/dozzy-1/4.png` (Sdk), `illustrations/dozzy-1/13.png` (Contribute),
    `illustrations/sigma-1/2.png` (Instructors), `illustrations/sketchy-1/17-dark.png` (Integrations)
  - `svg/brand-logos/react.svg` and `python-5.svg` (Sdk), `google-tag-manager.svg` (Integrations)
- **The VS Code logo**, at `/static/images/vs-code-logo.png` (VSCodeExtension). Library mode would
  inline it, and it is 115 kB.

The widgets' other logos are [Simple Icons](https://simpleicons.org/) (CC0), and are inlined in
the library.

### Text and translations

The widgets' text is English. In the web console, which defines Django's JavaScript catalog
(`window.django`), it is translated into the user's language.

## Props

Outside a web console, pass the urls of a platform, and set the cards' widths to fit the page.

| Widget         | Prop         | Default                                           | Purpose                                          |
| -------------- | ------------ | ------------------------------------------------- | ------------------------------------------------ |
| `Sdk`          | `openapiUrl` | `/docs/openapi/`                                  | The API reference button's url                   |
| `McpServer`    | `serverUrl`  | the page's domain, `/api/v1/mcp/smarter-project/` | The MCP server's url, in the Claude Code command |
| `Cli`          | `className`  | `col-xl-4`                                        | The card's grid column classes                   |
| `Instructors`  | `className`  | `col-xl-6`                                        | The card's grid column classes                   |
| `Integrations` | `className`  | `col-xl-4`                                        | The card's grid column classes                   |
| `Sdk`          | `className`  | `col-xl-4`                                        | The card's grid column classes                   |

The other widgets have no props. They fill the element that holds them.

## Development

The package is part of the Smarter web console's npm workspace, in
[smarter/react/packages/smarter.sh-widgets](https://github.com/smarter-sh/smarter/tree/main/smarter/react/packages/smarter.sh-widgets).

```console
cd smarter/react
npx vitest run --project smarter.sh-widgets           # tests, including every story
npm run build:lib -w @smarter.sh/ui-widgets         # dist/
npm run check:dist -w @smarter.sh/ui-widgets        # checks dist/ before it is published
make react-storybook APP=smarter.sh-widgets           # Storybook, from the repository's root
```

Each Smarter release publishes the package, at the platform's version:
`.github/workflows/uiWidgetsRelease.yml`. In the workspace, its version stays at the one that the
web console's dashboard depends on.

## License

AGPL-3.0-or-later
