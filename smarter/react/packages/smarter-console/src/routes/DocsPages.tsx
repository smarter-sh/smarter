/**
 * The docs pages of the manifests: what a manifest is and every kind's example (/docs/manifests), what the JSON
 * Schemas are for and every kind's (/docs/json-schemas), and one kind's example manifest or JSON Schema
 * (/docs/manifest/:kind, /docs/json-schema/:kind), from the public cli api. See lib/docs.
 */
import {
  asYaml,
  CodeBlock,
  gettext,
  highlightJson,
  highlightYaml,
  interpolate,
  interpolateNodes,
  plainLines,
  prettyJson,
} from "@smarter/common";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import type { ConsoleSession } from "@/contract.gen";
import {
  DOCS_TOOLS,
  JSON_SCHEMAS_PATH,
  jsonSchemaPath,
  kindOf,
  loadKindDocument,
  manifestPath,
  MANIFESTS_PATH,
  type KindDocument,
} from "@/lib/docs";
import { DocsArticle } from "@/routes/DocsLayout";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { useConsoleSession } from "@/session/context";

/** The layout of every manifest, which the Manifests page explains. It is YAML, and isn't translated. */
const MANIFEST_LAYOUT = `apiVersion: smarter.sh/v1
kind: LLMClient
metadata:
  # what identifies the resource in your account.
  name: my_llmclient
  description: A short, human-readable description.
  version: 1.0.0
spec:
  # the resource's configuration, which is different for each kind.
status:
  # read-only: the platform fills it in.
`;

/** Code, in the page's text. */
const code = (text: string) => <code>{text}</code>;

/** A link to each kind's page, in a grid. */
function KindLinks({ kinds, pathOf }: { kinds: string[]; pathOf: (kind: string) => string }) {
  return (
    <ul className="row g-3 list-unstyled mb-0">
      {kinds.map((kind) => (
        <li key={kind} className="col-6 col-md-4">
          <Link
            to={pathOf(kind)}
            className="d-block h-100 rounded border border-gray-300 px-4 py-3 fw-semibold text-gray-800 text-hover-primary"
          >
            {kind}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** The session, which the router's SessionProvider has loaded before a docs page renders. */
function useLoadedSession(): ConsoleSession | null {
  return useConsoleSession().session;
}

/** /docs/manifests: what a manifest is, how to apply one, and every kind's example. */
export function ManifestsPage() {
  const session = useLoadedSession();
  if (!session) return null;

  return (
    <DocsArticle>
      <h1 className="fs-2x fw-bold mb-6">{gettext("Smarter Manifests")}</h1>
      <p className="fs-5">
        {gettext(
          "A Smarter manifest is a YAML document that describes one resource of your platform: an LLMClient, a " +
            "plugin, a connection, a secret, and so on. Manifests are modeled on Kubernetes manifests: you keep them " +
            "in files, apply them, and the platform creates or updates the resource to match.",
        )}
      </p>

      <h2 className="fs-3 fw-bold mt-10 mb-4">{gettext("Anatomy of a manifest")}</h2>
      <p className="fs-5">
        {interpolateNodes(
          gettext(
            "Every manifest has the same parts: %(apiVersion)s, the version of the manifest format; %(kind)s, the " +
              "kind of resource; %(metadata)s, its name, description, version, tags and annotations; %(spec)s, its " +
              "configuration, which is different for each kind; and %(status)s, its read-only state, which the " +
              "platform fills in.",
          ),
          {
            apiVersion: code("apiVersion"),
            kind: code("kind"),
            metadata: code("metadata"),
            spec: code("spec"),
            status: code("status"),
          },
        )}
      </p>
      <CodeBlock lines={highlightYaml(MANIFEST_LAYOUT)} label={gettext("The layout of a manifest")} />

      <h2 className="fs-3 fw-bold mt-10 mb-4">{gettext("Applying a manifest")}</h2>
      <p className="fs-5">
        {interpolateNodes(
          gettext(
            "Apply a manifest with the %(cli)s. To start from an example, open a kind below, or print one with " +
              "the CLI:",
          ),
          { cli: <a href={DOCS_TOOLS.cli}>{gettext("Smarter CLI")}</a> },
        )}
      </p>
      <CodeBlock
        lines={plainLines("smarter manifest llmclient -o yaml > my-llmclient.yaml\nsmarter apply -f my-llmclient.yaml")}
        label={gettext("Smarter CLI commands")}
      />

      <h2 className="fs-3 fw-bold mt-10 mb-4">{gettext("Example manifests")}</h2>
      <p className="fs-5">{gettext("Each kind of resource has an example manifest.")}</p>
      <KindLinks kinds={session.samKinds} pathOf={manifestPath} />

      <p className="fs-5 mt-10 mb-0">
        {interpolateNodes(
          gettext(
            "The manifest format, smarter.sh/v1, is published as a JSON Schema of each kind, which editors and " +
              "other tools validate manifests against. See %(schemas)s.",
          ),
          { schemas: <Link to={JSON_SCHEMAS_PATH}>{gettext("JSON Schemas")}</Link> },
        )}
      </p>
    </DocsArticle>
  );
}

/** /docs/json-schemas: what the JSON Schemas are for, and every kind's. */
export function JsonSchemasPage() {
  const session = useLoadedSession();
  if (!session) return null;

  const uses = [
    {
      heading: gettext("Validation"),
      text: gettext("Check a manifest before you apply it, in your own code or in a CI pipeline."),
    },
    {
      heading: gettext("Editor support"),
      text: interpolateNodes(
        gettext(
          "The %(extension)s uses them for autocompletion, hover help and validation of manifest files, and " +
            "other editors can too.",
        ),
        { extension: <a href={DOCS_TOOLS.vscode}>{gettext("Smarter VS Code extension")}</a> },
      ),
    },
    {
      heading: gettext("Code generation"),
      text: gettext("Generate the types of your language from them, rather than writing them by hand."),
    },
    {
      heading: gettext("Integrations"),
      text: gettext("Build your own tools that read or write Smarter manifests."),
    },
  ];

  return (
    <DocsArticle>
      <h1 className="fs-2x fw-bold mb-6">{gettext("Manifest JSON Schemas")}</h1>
      <p className="fs-5">
        {gettext(
          "Each kind of Smarter manifest has a JSON Schema (draft 2020-12) that describes the smarter.sh/v1 " +
            "format exactly: every field, its type, whether it is required, and what it means.",
        )}
      </p>

      <h2 className="fs-3 fw-bold mt-10 mb-4">{gettext("What they are for")}</h2>
      <dl className="row g-4 mb-0">
        {uses.map((use) => (
          <div key={use.heading} className="col-md-6">
            <div className="h-100 rounded border border-gray-300 p-5">
              <dt className="fs-5 fw-bold mb-2">{use.heading}</dt>
              <dd className="mb-0">{use.text}</dd>
            </div>
          </div>
        ))}
      </dl>

      <h2 className="fs-3 fw-bold mt-10 mb-4">{gettext("JSON Schemas")}</h2>
      <p className="fs-5">
        {interpolateNodes(
          gettext(
            "The api returns each one at %(url)s, and the %(manifests)s show an example of each kind that follows it.",
          ),
          {
            url: code("/api/v1/cli/json-schema/<kind>/"),
            manifests: <Link to={MANIFESTS_PATH}>{gettext("example manifests")}</Link>,
          },
        )}
      </p>
      <KindLinks kinds={session.samKinds} pathOf={jsonSchemaPath} />
    </DocsArticle>
  );
}

type Loaded = { state: "loading" } | { state: "loaded"; data: Record<string, unknown> } | { state: "error" };

/**
 * A kind's example manifest or JSON Schema, from the cli api.
 *
 * @param document - Which of the two.
 * @param kind - The kind, or null for none.
 * @param session - The session, for the POST's CSRF token.
 * @returns The document, or whether it is loading or failed to load. A new kind is loading until its own answer
 *   arrives.
 */
function useKindDocument(document: KindDocument, kind: string | null, session: ConsoleSession | null): Loaded {
  const [loaded, setLoaded] = useState<Loaded & { key: string }>({ state: "loading", key: "" });
  const key = `${document}:${kind}`;
  const cookies = session?.cookies;

  useEffect(() => {
    if (!kind || !cookies) return;
    let cancelled = false;
    loadKindDocument(document, kind, cookies).then(
      (data) => {
        if (!cancelled) setLoaded({ state: "loaded", data, key });
      },
      () => {
        if (!cancelled) setLoaded({ state: "error", key });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [document, kind, cookies, key]);

  if (loaded.key !== key) return { state: "loading" };
  return loaded;
}

/** /docs/manifest/:kind and /docs/json-schema/:kind: a kind's example manifest, as YAML, or its JSON Schema. */
export function KindDocumentPage({ document }: { document: KindDocument }) {
  const session = useLoadedSession();
  const { kind: slug = "" } = useParams();
  const kind = session ? kindOf(slug, session.samKinds) : null;
  const loaded = useKindDocument(document, kind, session);

  if (!session) return null;
  if (!kind) return <NotFoundPage />;

  const isManifest = document === "manifest";
  const title = isManifest
    ? interpolate(gettext("%(kind)s example manifest"), { kind })
    : interpolate(gettext("%(kind)s JSON Schema"), { kind });

  return (
    <DocsArticle>
      <h1 className="fs-2x fw-bold mb-4">{title}</h1>
      <p className="fs-6 mb-6 d-flex flex-wrap gap-4">
        {isManifest ? (
          <>
            <Link to={jsonSchemaPath(kind)}>{interpolate(gettext("%(kind)s JSON Schema"), { kind })}</Link>
            <Link to={MANIFESTS_PATH}>{gettext("All example manifests")}</Link>
          </>
        ) : (
          <>
            <Link to={manifestPath(kind)}>{interpolate(gettext("%(kind)s example manifest"), { kind })}</Link>
            <Link to={JSON_SCHEMAS_PATH}>{gettext("All JSON Schemas")}</Link>
          </>
        )}
      </p>
      {loaded.state === "loading" && <p className="text-gray-600">{gettext("Loading…")}</p>}
      {loaded.state === "error" && (
        <div className="alert alert-danger" role="alert">
          {interpolate(gettext("%(title)s couldn't be loaded. Try again later."), { title })}
        </div>
      )}
      {loaded.state === "loaded" && (
        <CodeBlock
          lines={isManifest ? highlightYaml(asYaml(loaded.data)) : highlightJson(prettyJson(loaded.data))}
          label={title}
        />
      )}
    </DocsArticle>
  );
}

/** /docs/manifest/:kind. */
export function KindManifestPage() {
  return <KindDocumentPage document="manifest" />;
}

/** /docs/json-schema/:kind. */
export function KindJsonSchemaPage() {
  return <KindDocumentPage document="json-schema" />;
}
