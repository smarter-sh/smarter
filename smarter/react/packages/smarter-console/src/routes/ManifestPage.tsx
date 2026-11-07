/**
 * A resource's manifest page, e.g. /guardrail/guardrails/<hashed id>: the resource's name, and its manifest in
 * @smarter/manifest-editor, where it can be validated, saved, cloned and deleted with the cli api. The manifest
 * comes from the resource api, which finds the resource by its record locator if the user may read it, and
 * describes it as its owner does. After a delete, the page goes back to the resource's list.
 */
import { gettext } from "@smarter/common";
import { ManifestEditor } from "@smarter/manifest-editor";
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router";

import { djangoSessionContext } from "@/lib/djangoSession";
import {
  KIND_PLACEHOLDER,
  manifestEditorUrls,
  recordLocator,
  type ManifestPage as ManifestPageConfig,
} from "@/lib/manifestPages";
import { useResource } from "@/lib/useResource";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { useConsoleSession } from "@/session/context";

export function ManifestPage({ page }: { page: ManifestPageConfig }) {
  const { session } = useConsoleSession();
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const current = useResource(recordLocator(page, id));
  const sessionContext = useMemo(
    () => (session ? djangoSessionContext(session, manifestEditorUrls.apply) : null),
    [session],
  );

  if (!session || !sessionContext) return null;
  if (page.visible && !page.visible(session)) return <NotFoundPage />;
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
        {gettext("The manifest could not be loaded.")}
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
