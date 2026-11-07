/**
 * A resource's manifest page, e.g. /guardrail/guardrails/<hashed id>: the resource's name, and its manifest in
 * @smarter/manifest-editor, where it can be validated, saved, cloned and deleted with the cli api. The manifest
 * comes from the resource api, which finds the resource by its record locator if the user may read it, and
 * describes it as its owner does. After a delete, the page goes back to the resource's list.
 */
import { gettext } from "@smarter/common";
import { ManifestEditor } from "@smarter/manifest-editor";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";

import { ApiError, getJson } from "@/lib/api";
import { djangoSessionContext } from "@/lib/djangoSession";
import {
  KIND_PLACEHOLDER,
  manifestEditorUrls,
  recordLocator,
  resourceUrl,
  type ManifestPage as ManifestPageConfig,
} from "@/lib/manifestPages";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { useConsoleSession } from "@/session/context";

/** What the page reads of the resource api's answer. See smarter.apps.dashboard.resource_detail.ResourceDetail. */
interface ResourceManifest {
  kind: string;
  name: string | null;
  recordLocator: string;
  manifest: string | null;
  manifestError: string;
}

type Loaded =
  | { state: "loading"; locator: string }
  | { state: "found"; locator: string; resource: ResourceManifest }
  | { state: "not-found"; locator: string }
  | { state: "error"; locator: string; message: string };

export function ManifestPage({ page }: { page: ManifestPageConfig }) {
  const { session } = useConsoleSession();
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const locator = recordLocator(page, id);
  const [loaded, setLoaded] = useState<Loaded>({ state: "loading", locator });
  const sessionContext = useMemo(
    () => (session ? djangoSessionContext(session, manifestEditorUrls.apply) : null),
    [session],
  );

  useEffect(() => {
    let cancelled = false;
    getJson<ResourceManifest>(resourceUrl(locator)).then(
      (resource) => {
        if (!cancelled) setLoaded({ state: "found", locator, resource });
      },
      (e: unknown) => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 404) {
          setLoaded({ state: "not-found", locator });
        } else {
          setLoaded({ state: "error", locator, message: gettext("The manifest could not be loaded.") });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [locator]);

  if (!session || !sessionContext) return null;
  if (page.visible && !page.visible(session)) return <NotFoundPage />;
  // a page whose id changed shows that it is loading, not the previous resource.
  const current: Loaded = loaded.locator === locator ? loaded : { state: "loading", locator };
  if (current.state === "loading") {
    return (
      <p role="status" className="mt-5">
        {gettext("Loading...")}
      </p>
    );
  }
  if (current.state === "not-found") return <NotFoundPage />;
  if (current.state === "error") {
    return (
      <div role="alert" className="alert alert-danger mt-5">
        {current.message}
      </div>
    );
  }
  const { resource } = current;
  return (
    <section className="row g-5 g-xl-10 mt-1" aria-label={resource.name ?? resource.kind}>
      <div className="col-xl-8 mb-5 mb-xl-10">
        <h2>{resource.name ?? resource.kind}</h2>
        {resource.manifest === null ? (
          <div role="alert" className="alert alert-warning">
            {resource.manifestError || gettext("The manifest could not be loaded.")}
          </div>
        ) : (
          <ManifestEditor
            sessionContext={sessionContext}
            initialManifest={resource.manifest}
            applyApiUrl={manifestEditorUrls.apply}
            validateApiUrl={manifestEditorUrls.validate}
            deleteApiUrl={manifestEditorUrls.delete}
            kindPlaceholder={KIND_PLACEHOLDER}
            onDeleted={() => void navigate(page.listPath)}
          />
        )}
      </div>
    </section>
  );
}
