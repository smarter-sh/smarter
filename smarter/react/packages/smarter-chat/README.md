# @smarter.sh/ui-chat

> The official chat UI for [Smarter](https://smarter.sh) LLMClients. Drop it into any website, whether React, Next.js,
> WordPress, Django, Flask, Node.js or plain HTML, and it gets its behavior and its look from the LLMClient's YAML
> manifest.

[![GitHub](https://img.shields.io/badge/github-smarter--sh%2Fsmarter--chat-181717?logo=github)](https://github.com/smarter-sh/smarter-chat)
[![npm version](https://img.shields.io/npm/v/@smarter.sh/ui-chat?logo=npm)](https://www.npmjs.com/package/@smarter.sh/ui-chat)
[![npm downloads](https://img.shields.io/npm/dm/@smarter.sh/ui-chat)](https://www.npmjs.com/package/@smarter.sh/ui-chat)
[![Test Status](https://github.com/smarter-sh/smarter-chat/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/smarter-sh/smarter-chat/actions/workflows/test.yml)
[![Docs](https://img.shields.io/badge/Read%20the%20Docs-smarter.sh-blue?logo=readthedocs)](https://docs.smarter.sh/smarter-framework/smarter-chat.html)
[![Coverage](https://img.shields.io/codecov/c/github/smarter-sh/smarter-chat/main?label=coverage&logo=codecov)](https://app.codecov.io/gh/smarter-sh/smarter-chat)
[![TypeScript](https://img.shields.io/badge/types-included-blue?logo=typescript&logoColor=white)](#typescript)
[![React 19](https://img.shields.io/badge/react-19-61dafb?logo=react&logoColor=white)](https://react.dev)
[![License: AGPL-3.0-or-later](https://img.shields.io/npm/l/@smarter.sh/ui-chat)](https://github.com/smarter-sh/smarter-chat/blob/main/LICENSE)

![Smarter Chat](https://cdn.smarter.sh/images/smarter-chat-ui-example.png)

Smarter Chat is the chat window of the Smarter web console's prompt engineering workbench, published on npm so you can
put the same chat on your own website: a marketing site, a customer portal, a storefront, an intranet or an application.
You build and run the chatbot on Smarter, and this package displays it on your pages. The complete guide is at
[docs.smarter.sh](https://docs.smarter.sh/smarter-framework/smarter-chat.html).

**[Documentation](https://docs.smarter.sh/smarter-framework/smarter-chat.html)** ·
**[Storybook](#development)** · **[Changelog](https://github.com/smarter-sh/smarter-chat/blob/main/CHANGELOG.md)** ·
**[Issues](https://github.com/smarter-sh/smarter-chat/issues)**

## Contents

- [How it works](#how-it-works)
- [Features](#features)
- [Installation](#installation)
- [Quick start (React)](#quick-start-react)
- [Embedding in any website](#embedding-in-any-website)
- [Requirements on the Smarter side](#requirements-on-the-smarter-side)
- [Behavior: `spec.config.prompt`](#behavior-specconfigprompt)
- [Styling: `spec.config.styles`](#styling-specconfigstyles)
- [Props](#props)
- [More examples](#more-examples)
- [TypeScript](#typescript)
- [The api contract](#the-api-contract)
- [Browser support](#browser-support)
- [Development](#development)
- [License](#license)

## How it works

Smarter Chat isn't a general-purpose chat UI. It works only with a Smarter
[LLMClient](https://docs.smarter.sh/smarter-resources/smarter-llmclient.html), which is a chatbot that you declare in a
YAML manifest and apply to a Smarter platform with the `smarter` CLI or the REST API. The platform runs the
chatbot, and this component is its front end. It can't call OpenAI, Anthropic or any other LLM provider directly.

The `SmarterChat` component has a single required prop, `apiUrl`, which is the url of a deployed LLMClient. Everything
else comes from the LLMClient's manifest, so you change the chat by applying a new manifest, not by redeploying your
website:

| You want to change                                                                                                                                                                         | Where it's set                                                                                                |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| What the chatbot says and does: its LLM, model, system prompt, name, welcome message and examples                                                                                          | The manifest's [`spec.config.prompt`](#behavior-specconfigprompt)                                             |
| Its tools and safety: [Plugins](https://docs.smarter.sh/smarter-resources/smarter-llmtool.html), Functions, [Guardrails](https://docs.smarter.sh/smarter-resources/smarter-guardrail.html) | The manifest's `spec.plugins`, `spec.functions` and `spec.guardrails`                                         |
| How it looks: its logo, avatars, background image, font and colors                                                                                                                         | The manifest's [`spec.config.styles`](#styling-specconfigstyles)                                              |
| Where it appears on your page and its size, plus any extra CSS                                                                                                                             | Your page: the component's [props](#props) and your [stylesheet](#your-own-css)                               |
| The data exchanged between browser and server                                                                                                                                              | [The api contract](#the-api-contract), generated from Smarter's Pydantic models. You don't change it yourself |

```yaml
apiVersion: smarter.sh/v1
kind: LLMClient
metadata:
  name: support
  description: Customer support for example.com
  version: 1.0.0
spec:
  config:
    prompt: # behavior: what the chatbot is and does
      deployed: true
      provider: openai
      defaultModel: gpt-4o-mini
      defaultSystemRole: You are a friendly support agent for example.com. Answer briefly.
      appName: Example Support
      appAssistant: Sam
      appWelcomeMessage: Hi, I'm Sam. How can I help?
      appExamplePrompts:
        - How do I reset my password?
        - What is your return policy?
      appPlaceholder: Ask me anything...
      allowedOrigins:
        - https://www.example.com
    styles: # look: how the chat is displayed, on every page that embeds it
      appLogoUrl: https://cdn.example.com/logo.png
      googleFont: Nunito
      conversationHeader: { backgroundColor: "#14213d", color: "#ffffff" }
      outgoingMessage: { backgroundColor: "#fca311", color: "#14213d" }
  plugins:
    - order-status
```

```tsx
<SmarterChat apiUrl="https://support.3141-5926-5359.api.example.com/" />
```

## Features

- **Configured by its manifest.** You give it the url of a deployed LLMClient, and it loads the LLMClient's name,
  welcome message, example prompts, placeholder and styles from Smarter.
- **Embed it anywhere.** You can use it as a React component, or build it once into a small script that WordPress,
  Django, Flask, Express or a plain HTML page includes.
- **Themeable without CSS.** The logo, avatars, background image, Google font, font size, corner radius and the colors
  of every part of the chat are set in the manifest and validated by Smarter.
- **Persistent chat sessions.** The conversation survives page reloads, and each LLMClient on a site keeps its own
  session.
- **Live progress.** While a prompt runs, the chat shows each LLM request and each tool, Plugin and MCP server call,
  streamed as Server-Sent Events.
- **Rich responses.** It renders GitHub flavored markdown (tables, lists, block quotes, images, links),
  syntax-highlighted code blocks with a copy button, LaTeX math typeset by [KaTeX](https://katex.org), and
  [Mermaid](https://mermaid.js.org) diagrams.
- **Safe by default.** Raw HTML is displayed as text. Links and images are restricted to `http(s)`, relative and
  raster `data:` urls. The rendered HTML and Mermaid's SVG are sanitized with
  [DOMPurify](https://github.com/cure53/DOMPurify).
- **Lightweight where it counts.** React is a peer dependency. Mermaid is loaded only when a message first has a
  diagram, and KaTeX's fonts are downloaded only when an equation uses them.
- **Made to be hosted.** A page can follow the chat (`onConfig`, `onNewChat`, `onModeChange`), ask it for the
  configuration's diagnostic parts (`verbose`) or to reload it (`reloadKey`), and add its own buttons to the chat's
  header (`headerActions`). The Smarter web console's workbench puts its developer Console beside the chat this way.
- **Accessible.** It has labeled regions and controls, keyboard-resizable panels, and MathML for screen readers.
- **Translated.** Its own text is in English, Spanish, French or Brazilian Portuguese: the page's language, or the one
  you ask for. The LLMClient's welcome message, example prompts and responses are displayed as they are.
- **Typed.** It's written in TypeScript, and its types are generated from Smarter's api contract.

See [Features](https://docs.smarter.sh/smarter-framework/smarter-chat/features.html) for details.

## Installation

```console
npm install @smarter.sh/ui-chat
```

```console
yarn add @smarter.sh/ui-chat
```

```console
pnpm add @smarter.sh/ui-chat
```

`react` and `react-dom` 19 are peer dependencies. The package is published as ES and UMD bundles, and is meant to be
used with a bundler such as Vite, webpack, Rollup or Next.js. If your site isn't built with React, see
[Embedding in any website](#embedding-in-any-website).

## Quick start (React)

```tsx
import { createRoot } from "react-dom/client";
import { SmarterChat } from "@smarter.sh/ui-chat";
import "@smarter.sh/ui-chat/dist/ui-chat.css";
import "katex/dist/katex.min.css"; // math in responses. katex is installed with the package.

createRoot(document.getElementById("chat")!).render(
  <div style={{ height: 600 }}>
    <SmarterChat
      apiUrl="https://stackademy.3141-5926-5359.api.example.com/"
      apiKey={import.meta.env.VITE_SMARTER_API_KEY} // only if the LLMClient has an api key
    />
  </div>,
);
```

The chat fills the height of its parent element, so give the parent a height. Before it can connect, the LLMClient
must be deployed and must allow your page's origin. See
[Requirements on the Smarter side](#requirements-on-the-smarter-side).

## Embedding in any website

If your site isn't built with React, such as a WordPress, Drupal, Shopify, Squarespace or SharePoint site, a
documentation site, or a server-rendered or plain HTML page, add the **embed script**. It's one prebuilt file,
`dist/embed.js`, that includes React and Smarter Chat, so your page needs nothing else, and it renders the chat in a
[Shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM), so your site's theme
can't break it, and it can't change your site.

```html
<script
  src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js"
  data-chatbot="https://support.3141-5926-5359.api.example.com/"
  async
></script>
```

That adds a chat button to the bottom right corner of every page that has the tag. The button opens the chat, which
loads only then, and the conversation follows the visitor from page to page. To put the chat in the page instead, use
the `<smarter-chat>` element, wherever the script is loaded:

```html
<smarter-chat chatbot="https://support.3141-5926-5359.api.example.com/" height="600px"></smarter-chat>
```

### Options

The element's attributes, the script tag's `data-` attributes and the properties of `window.SmarterChatConfig` (in
camelCase, e.g. `apiKey`) are the same options. Only `chatbot` is required.

| Option                | Default               | Description                                                                                |
| --------------------- | --------------------- | ------------------------------------------------------------------------------------------ |
| `chatbot`             | (required)            | The deployed LLMClient's url.                                                              |
| `api-key`             |                       | A Smarter api key, for LLMClients that require one. It's public in the page.               |
| `mode`                | `launcher` / `inline` | `launcher` (the script tag's default) or `inline` (the element's default).                 |
| `position`            | `bottom-right`        | The launcher's corner: `bottom-right` or `bottom-left`.                                    |
| `open`                | `false`               | Start with the launcher open.                                                              |
| `label`               | `Chat`                | The launcher's accessible name.                                                            |
| `color`               | `#ff5733`             | The launcher button's color.                                                               |
| `width`, `height`     | `400px`, `600px`      | The launcher's panel, or the inline chat (`100%`, `600px`). Any css length.                |
| `z-index`             | `2147483000`          | The launcher's stacking order.                                                             |
| `session-cookie-name` | one per chatbot host  | The cookie that keeps the chat session.                                                    |
| `cookie-path`         | `/`                   | The session cookie's path. `/` keeps one conversation across the whole site.               |
| `stream-progress`     | `true`                | Show a running prompt's steps, e.g. its tool calls.                                        |
| `debug`               | `false`               | Log to the browser console.                                                                |
| `language`            | the page's            | The chat's own language: `en`, `es`, `fr` or `pt-br`, or a regional variant, e.g. `es-MX`. |

| `target` | | Script tag and `SmarterChatConfig` only: a css selector to render the chat inline in. |

Where you can't set a script tag's attributes, as in Google Tag Manager, set `window.SmarterChatConfig` (an object, or
an array of them) before the script runs:

```html
<script>
  window.SmarterChatConfig = { chatbot: "https://support.3141-5926-5359.api.example.com/", position: "bottom-left" };
</script>
<script src="https://cdn.jsdelivr.net/npm/@smarter.sh/ui-chat@0/dist/embed.js" async></script>
```

Your own buttons can open the launcher with `SmarterChat.open()`, `SmarterChat.close()` and `SmarterChat.toggle()`,
and the element dispatches a `smarter-chat-toggle` event, with `event.detail.open`, when it opens or closes. Style the
launcher from your css with `smarter-chat::part(launcher)`, `::part(panel)` and `::part(chat)`.

### Hosting the script yourself

`embed.js` loads its other files from an `embed/` directory beside it: Mermaid, which is downloaded only when a
message has a diagram, and KaTeX's fonts, only when one has math. To serve it from your own site, copy `dist/embed.js`
and `dist/embed/` together, e.g. from `npm pack @smarter.sh/ui-chat`. Pin a version (`@0.9.0`) on a CDN url if you want
to review changes before your visitors see them; `@0` follows the latest 0.x release.

### Platforms

Plugins that write the tag for you, with a settings screen:
[WordPress](https://github.com/smarter-sh/smarter-wordpress), [Drupal](https://github.com/smarter-sh/smarter-drupal),
[Shopify](https://github.com/smarter-sh/smarter-shopify),
[Google Tag Manager](https://github.com/smarter-sh/smarter-gtm-template), and Docusaurus, MkDocs, Sphinx and VitePress
([smarter-docs-site-generators](https://github.com/smarter-sh/smarter-docs-site-generators)). Every other platform that
lets you add a script to its pages needs only the tag above. See
[Embedding Smarter Chat](https://docs.smarter.sh/smarter-framework/smarter-chat/embedding.html).

## Requirements on the Smarter side

The component calls the Smarter platform directly from your visitors' browsers, so three things must be true:

1. **The LLMClient is deployed** (`spec.config.prompt.deployed: true`). `apiUrl` is its url, for example
   `https://<name>.<account-number>.api.<your-smarter-domain>/`, or its verified
   [custom domain](https://docs.smarter.sh/smarter-resources/smarter-custom-domain.html). The chat calls only
   that host.
2. **Your page's origin is allowed.** Requests from your page are cross-origin and include credentials, so list your
   site's origins in the LLMClient's manifest and apply it:

   ```yaml
   spec:
     config:
       prompt:
         allowedOrigins:
           - https://www.example.com
           - http://localhost:5173
   ```

3. **The browser can authenticate, if the LLMClient requires it.** A deployed LLMClient without api keys is public.
   Pass no `apiKey`, and every prompt is charged to the LLMClient's owner. If the LLMClient has an api key, pass a
   [Smarter api key](https://docs.smarter.sh/smarter-resources/smarter-authtoken.html) as `apiKey`, which is sent as `Authorization: Token <apiKey>`. Anyone who can view your page can
   read it, so create a key just for that page.

The page receives only the LLMClient's public configuration (its name, welcome message, example prompts, model,
system prompt and styles). It never receives, for example, its owner's profile or the session's diagnostic history.

For details and troubleshooting, see
[Embedding Smarter Chat](https://docs.smarter.sh/smarter-framework/smarter-chat/embedding.html).

## Behavior: `spec.config.prompt`

You configure the chatbot's behavior in its manifest, not in this package. The section is validated on the platform by
the Pydantic model
[`SAMLLMClientSpecConfigPrompt`](https://docs.smarter.sh/smarter-resources/llmclient/sam.html)
(`smarter.apps.llmclient.manifest.models.llmclient.spec`). The settings fall into three groups: what Smarter sends to the
LLM, what the chat displays, and who may use it.

| Setting                                  | Effect in the chat                                                                                                           |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `provider`, `defaultModel`               | The LLM that answers. They're also shown under the name in the header, as in "openai gpt-4o-mini with 2 additional plugins". |
| `defaultSystemRole`                      | The system prompt that starts every new session. It's visible in the workbench's sandbox mode.                               |
| `defaultTemperature`, `defaultMaxTokens` | Sent to the LLM with each prompt.                                                                                            |
| `appName`                                | The title in the header, followed by the manifest's `metadata.version`.                                                      |
| `appAssistant`                           | The sender name on the assistant's messages. The default is "Assistant".                                                     |
| `appWelcomeMessage`                      | The first assistant message of a new session.                                                                                |
| `appExamplePrompts`                      | A second assistant message that lists them: "Some example prompts to get you started".                                       |
| `appPlaceholder`                         | The hint in the empty message box.                                                                                           |
| `appFileAttachment`                      | Shows the attach button in the message box.                                                                                  |
| `deployed`, `subdomain`, `customDomain`  | Whether the LLMClient has a public url, and what that url is, which you pass as `apiUrl`.                                    |
| `allowedOrigins`                         | The websites that may embed the chat.                                                                                        |

The chatbot's tools are set beside `config`: `spec.plugins`, `spec.functions` and `spec.guardrails` are run by the
platform. The chat displays their calls as progress while a prompt runs.

Apply a changed manifest with `smarter apply -f llmclient.yaml`. A new chat session picks up the change without any
change to your website.

## Styling: `spec.config.styles`

### The LLMClient's styles

The chat takes its look from the LLMClient's manifest, so most pages need no CSS of their own. `spec.config.styles` is
validated on the platform by the Pydantic model
[`SAMLLMClientSpecConfigStyles`](https://docs.smarter.sh/smarter-resources/llmclient/sam.html)
(`smarter.apps.llmclient.manifest.models.llmclient.styles`). Every setting is optional, and a setting that is left out
keeps the default. Colors, lengths and font names must be plain CSS values, and images must be `https` urls that
Smarter can fetch when the manifest is applied.

```yaml
spec:
  config:
    styles:
      # images
      appLogoUrl: https://cdn.example.com/logo.png # in a circle at the left of the header
      assistantAvatarUrl: https://cdn.example.com/assistant.png
      userAvatarUrl: https://cdn.example.com/user.png
      appBackgroundImageUrl: https://cdn.example.com/background.jpg
      appBackgroundImageSize: cover # cover | contain | auto
      # typography and shape
      googleFont: Nunito # downloaded from fonts.google.com
      fontFamily: '"Nunito", system-ui, sans-serif' # overrides googleFont's stack
      fontSize: 16px
      borderRadius: 0.7em
      # colors, one section per part of the chat
      mainContainer: { backgroundColor: "#ffffff", color: "#212121", borderColor: "#d1dbe3" }
      conversationHeader: { backgroundColor: "#14213d", color: "#ffffff", infoColor: "#c0c4e0", borderColor: "#14213d" }
      messageList: { backgroundColor: "rgba(255, 255, 255, 0.6)", color: "#212121" } # tints the background image
      incomingMessage: { backgroundColor: "#e5e5e5", color: "#14213d", borderColor: "#d1dbe3", linkColor: "#0b57d0" }
      outgoingMessage: { backgroundColor: "#fca311", color: "#14213d", linkColor: "#14213d" }
      messageInput:
        backgroundColor: "#ffffff"
        editorBackgroundColor: "#f6fbff"
        color: "#212121"
        placeholderColor: "#9e9e9e"
        borderColor: "#d1dbe3"
      buttons: { color: "#fca311" }
      typingIndicator: { color: "#fca311" }
```

The sections correspond to the [chatscope](https://github.com/chatscope/chat-ui-kit-react) components that the chat is
built on: `MainContainer`, `ConversationHeader`, `MessageList`, `Message`, `MessageInput`, `Button` and
`TypingIndicator`. The same styles apply in the Smarter workbench and on every page that embeds the LLMClient.

The chat sets the styles as CSS custom properties on its root `.SmarterChat` element, such as
`--smarter-chat-header-bg` and `--smarter-chat-outgoing-bg`. Their fallbacks are chatscope's own colors. See
[Styling Your LLMClient's Chat](https://docs.smarter.sh/smarter-resources/llmclient/styles.html) for every
setting.

### Your own CSS

Import the stylesheets once, anywhere in your app:

```ts
import "@smarter.sh/ui-chat/dist/ui-chat.css"; // or "@smarter.sh/ui-chat/style.css"
import "katex/dist/katex.min.css";
```

- **`ui-chat.css`** is the component's own CSS, including chatscope's chat styles.
- **`katex/dist/katex.min.css`** styles math in responses. It's kept out of `ui-chat.css` so that pages without math
  don't download KaTeX's fonts. Without it, each equation is displayed twice, once as text and once as unstyled
  MathML.

The component's elements have stable class names prefixed `smarter-chat-` (for example `.smarter-chat-message-list`,
`.smarter-chat-code`, `.smarter-chat-image`), under a root `.SmarterChat` element. Your stylesheet can override them,
or set the `--smarter-chat-*` properties, for anything the manifest doesn't cover. If a setting is in the manifest,
prefer setting it there, so that it applies everywhere the LLMClient is embedded.

## Props

Only `apiUrl` is required.

| Prop                      | Type             | Default         | Description                                                                                                                                                         |
| ------------------------- | ---------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apiUrl`                  | `string`         | (required)      | The LLMClient's api url. The chat appends `config/` to it for its configuration.                                                                                    |
| `apiKey`                  | `string \| null` | `null`          | A Smarter api key, sent as `Authorization: Token <apiKey>`, for LLMClients that require authentication.                                                             |
| `streamProgress`          | `boolean`        | `true`          | Display a running prompt's progress, which the prompt api streams as Server-Sent Events.                                                                            |
| `debugMode`               | `boolean`        | `false`         | Log to the browser console.                                                                                                                                         |
| `cookieDomain`            | `string`         | `""`            | The domain whose cookies the chat reads. Empty means the page's own domain.                                                                                         |
| `sessionCookieName`       | `string`         | `"session_key"` | The cookie in which the chat saves its session's key, for the page's path.                                                                                          |
| `sessionCookieExpiration` | `number`         | one day         | The session cookie's lifetime, in milliseconds.                                                                                                                     |
| `csrfCookieName`          | `string`         | `"csrftoken"`   | The name of Django's CSRF cookie, whose value is sent as the `X-CSRFToken` header.                                                                                  |
| `csrftoken`               | `string \| null` | `null`          | The CSRF token, when the page cannot read the CSRF cookie.                                                                                                          |
| `debugCookieName`         | `string`         | `"debug"`       | The cookie in which the chat saves the LLMClient's debug mode.                                                                                                      |
| `debugCookieExpiration`   | `number`         | one day         | The debug cookie's lifetime, in milliseconds.                                                                                                                       |
| `smarterRequestId`        | `string`         | `""`            | A unique id of the page request, sent as the `X-Smarter-RequestId` header, for tracing.                                                                             |
| `language`                | `string \| null` | `null`          | The language of the chat's own text: `en`, `es`, `fr` or `pt-br`, or a regional variant, e.g. `es-MX`. By default, the page's `<html lang>`, or else the browser's. |
| `toggleMetadata`          | `boolean`        | `false`         | Show the Sandbox / Production mode switch, and start in sandbox mode, in which the thread also shows Smarter's system, tool and meta data messages.                 |

The props control where and how the chat runs on your page. Its content and look come from the manifest, so there is
no prop for the welcome message, the colors or the model.

## More examples

### A chat widget in a corner of the page

```tsx
function ChatWidget({ apiKey }: { apiKey: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(!open)}>Chat with us</button>
      {open && (
        <div style={{ position: "fixed", right: 24, bottom: 80, width: 400, height: 600 }}>
          <SmarterChat apiUrl="https://support.3141-5926-5359.api.example.com/" apiKey={apiKey} />
        </div>
      )}
    </>
  );
}
```

### Next.js

The component uses browser apis (cookies, `localStorage`, `EventSource`), so render it on the client only:

```tsx
"use client";
import dynamic from "next/dynamic";
import "@smarter.sh/ui-chat/dist/ui-chat.css";
import "katex/dist/katex.min.css";

const SmarterChat = dynamic(() => import("@smarter.sh/ui-chat").then((m) => m.SmarterChat), { ssr: false });

export default function Chat() {
  return (
    <div style={{ height: "80vh" }}>
      <SmarterChat
        apiUrl="https://stackademy.3141-5926-5359.api.example.com/"
        apiKey={process.env.NEXT_PUBLIC_SMARTER_API_KEY}
      />
    </div>
  );
}
```

### A page that hosts the chat

These props let a page follow the chat, and add to it. The Smarter web console's prompt engineering workbench, which
imports this package, puts its developer Console beside the chat with them.

| Prop            | Type                           | Description                                                                                                       |
| --------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `verbose`       | `boolean`                      | Fetch the configuration's diagnostic parts too, e.g. the session's tool calls, and again after each prompt.       |
| `onConfig`      | `(config: ChatConfig) => void` | Called with the configuration each time it loads.                                                                 |
| `onNewChat`     | `() => void`                   | Called when the user starts a new chat.                                                                           |
| `onModeChange`  | `(sandbox: boolean) => void`   | Called with whether the chat is in sandbox mode, when it starts and when the user switches.                       |
| `reloadKey`     | `number \| string`             | Reload the configuration when it changes, e.g. after the page changed the LLMClient's manifest.                   |
| `headerActions` | `ReactNode`                    | Buttons that the page adds to the chat's header, after its own. `HeaderButton` looks like the chat's own buttons. |

```tsx
import { HeaderButton, SmarterChat, type ChatConfig } from "@smarter.sh/ui-chat";

function HostedChat() {
  const [config, setConfig] = useState<ChatConfig | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  return (
    <SmarterChat
      apiUrl="https://stackademy.3141-5926-5359.api.example.com/"
      onConfig={setConfig}
      reloadKey={reloadKey}
      headerActions={<HeaderButton onClick={() => setReloadKey((key) => key + 1)}>Reload</HeaderButton>}
    />
  );
}
```

## TypeScript

Type declarations are included. Besides the components, the package exports:

| Export                                                            | What it is                                                         |
| ----------------------------------------------------------------- | ------------------------------------------------------------------ |
| `SmarterChat`                                                     | The chat component.                                                |
| `HeaderButton`, `HeaderButtonProps`                               | A button of the chat's header, for `headerActions`.                |
| `SmarterChatProps`                                                | The chat's props.                                                  |
| `ChatConfig`, `LLMClientConfig`, `ChatHistory`, `ChatMetaData`    | The LLMClient configuration that the Smarter config api returns.   |
| `Contract`                                                        | Every type of the api contract, generated from its JSON Schema.    |
| `normalizeConfig`, `CHAT_CONTRACT_V2_CAPABILITY`                  | Converts an older platform's configuration to the current version. |
| `ApiMessage`, `ChatMessage`                                       | A message as the api sends it, and as the chat thread holds it.    |
| `PromptProgressEvent`                                             | A step of a running prompt, as the prompt api streams it.          |
| `MessageDirectionEnum`, `SenderRoleEnum`, `ValidMessageRolesEnum` | Message directions and roles.                                      |
| `version`                                                         | The package's version.                                             |

## The api contract

The component and the Smarter platform share a single, versioned api contract. The contract is defined by Pydantic
models in the Smarter backend, in
[`smarter.apps.prompt.contract`](https://docs.smarter.sh/smarter-framework/smarter-chat/technical-reference/contract.html):

1. The platform builds its responses from those models.
2. `manage.py export_chat_contract_schema` exports the models as a JSON Schema, `chat-contract.schema.json`.
3. This package keeps a copy of the schema in `contract/`, generates its TypeScript types from it (`src/contract.gen.ts`,
   exported as `Contract`), and validates its test fixtures against it.

A change to the backend's models therefore reaches the component's types, and a test on each side fails if its copy of
the schema is out of date. This is why the component works only with a Smarter backend.

The component makes two kinds of POST requests to Smarter, with the browser's cookies:

1. **`<apiUrl>config/`** returns the LLMClient's public configuration, including its `spec.config.prompt` settings and
   its `styles`, plus the chat session's history, which restores the thread when the page reloads. A new session's key
   is saved in a cookie.
2. **The LLMClient's prompt api** (`llmclient.url_llmclient` in the configuration) receives the thread with each new
   message, and returns the messages to add to it. With `streamProgress`, it responds with Server-Sent Events: progress
   events while the prompt runs, then the result.

The component asks for version 2 of the contract with the `X-Smarter-Capabilities: chat-contract-v2` header. It also
reads version 1 from older Smarter platforms, and converts it with `normalizeConfig`.

The complete contract, with every request, response, header, cookie and event, is in
[The Chat API Contract](https://docs.smarter.sh/smarter-framework/smarter-chat/api-contract.html).

## Browser support

Smarter Chat supports current versions of Chrome, Edge, Firefox and Safari. It uses `fetch` response streams,
`EventSource`, `localStorage` and the `inert` attribute.

## Development

```console
git clone https://github.com/smarter-sh/smarter-chat.git
cd smarter-chat
make init    # npm install
make serve   # Storybook at http://localhost:6006, with the Smarter api mocked
make test    # Vitest; every story is also rendered as a test
```

You don't need a Smarter backend: the stories mock the api with [MSW](https://mswjs.io/), using fixtures that are
validated against the contract's schema. See
[CONTRIBUTING.md](https://github.com/smarter-sh/smarter-chat/blob/main/.github/CONTRIBUTING.md) for the rest of the
workflow (every `make` target, working inside the Smarter repository, commits and releases), and the
[developer guide](https://docs.smarter.sh/smarter-framework/smarter-chat/development.html) for the
architecture.

## License

[AGPL-3.0-or-later](https://github.com/smarter-sh/smarter-chat/blob/main/LICENSE), as Smarter is. Copyright © Lawrence
McDaniel.

Contributions are welcome: code, documentation, how-to videos, testing and community help. See
[CONTRIBUTING.md](https://github.com/smarter-sh/smarter-chat/blob/main/.github/CONTRIBUTING.md), or contact
[Lawrence McDaniel](https://lawrencemcdaniel.com/contact).
