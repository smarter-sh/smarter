# @smarter/llmclient-deployment

An LLMClient's deployment page. One app renders it in two places:

- **public**: the page that a browser sees at a deployed LLMClient's url, while the
  `enable_llmclient_endpoints_page` waffle switch is active:
  `smarter.apps.llmclient.views.endpoints.LLMClientEndpointsView`.
- **workbench**: the "Deployment" tab of the Console of the Prompt Engineer's Workbench (`@smarter/workbench`),
  whatever the switch, which renders the package's component, `DeploymentPage` (`src/index.ts`), with the
  data of `smarter.apps.prompt.views.detailviews.prompt_deployment_view.LLMClientDeploymentView`.

The page shows the LLMClient's status and url, the command that deploys it if it isn't deployed, the
integrations that put its chat on a web site, how to secure its url with an api key, how its url works,
with curl commands, how its chat sessions work, and its manifest. The workbench adds the LLMClient's owner, a guide to cloning it
for a user who may not change it, and manages its api key in place: it lists the account's api keys,
creates one, and attaches or detaches it. The public page adds The Smarter Project, which built it.

## Integration

- The page's data is an `LLMClientDeploymentPage`, from
  `smarter.apps.llmclient.views.deployment_contract`. The page at the deployed LLMClient's url has it in a
  `json_script`; the workbench fetches it when its tab is first opened.
- `contract/llmclient-deployment.schema.json` is the contract's JSON Schema, which the backend
  generates (`make llmclient-deployment-contract`), and `src/contract.gen.ts` its TypeScript types
  (`npm run contract:types`). `src/contract.test.ts` fails if either is out of date, or if a test
  fixture doesn't match the schema.
- The workbench's api key actions POST to the urls in the page's `apiKeys`, and answer with the page
  as it now is, and a new key's secret, once.
- `smarter.apps.llmclient.templatetags.react_llmclient_deployment` provides the app's assets, from
  its Vite `manifest.json`. `templates/llmclient/endpoints.html` renders the root element and the data.
- The package's source uses relative imports, so that the workbench's build can import it, and
  `@smarter/llmclient-deployment/mocks` exports its fixtures, for the workbench's tests and stories.
- The text is translated with the web console's `djangojs` catalog. A deployed LLMClient's own host
  serves it at `/jsi18n/`, as the web console does.

## Development

```console
npm run dev     # Vite dev server, with index.html's example page
npm run build   # builds into smarter/static/react/@smarter/llmclient-deployment/
npm run test
npm run lint
```
