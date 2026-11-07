/**
 * A resource from the resource api, by its record locator: the hook of the pages that show one resource, the
 * manifest pages and the workbench. The api finds the resource if the user may read it, by the backend's rule
 * (smarter.apps.dashboard.resource_detail.readable_instance), and answers 404 otherwise, as for one that doesn't exist,
 * so that a page shows Page not found for both.
 */
import { useEffect, useState } from "react";

import { ApiError, getJson } from "@/lib/api";
import { resourceUrl } from "@/lib/manifestPages";

/** What the pages read of the resource api's answer. See smarter.apps.dashboard.resource_detail.ResourceDetail. */
export interface ResourceManifest {
  kind: string;
  name: string | null;
  recordLocator: string;
  manifest: string | null;
  manifestError: string;
}

export type LoadedResource =
  { state: "loading" } | { state: "found"; resource: ResourceManifest } | { state: "not-found" } | { state: "error" };

type Loaded = LoadedResource & { locator: string };

/**
 * Load a resource by its record locator.
 *
 * @param locator - The record locator, e.g. guardrail-rMTAwx.
 * @returns The resource, or whether it is still loading, not found (or not readable), or failed to load. A new
 *   locator is loading until its own answer arrives, so that a page never shows the previous resource.
 */
export function useResource(locator: string): LoadedResource {
  const [loaded, setLoaded] = useState<Loaded>({ state: "loading", locator });

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
          setLoaded({ state: "error", locator });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [locator]);

  if (loaded.locator !== locator) return { state: "loading" };
  return loaded;
}
