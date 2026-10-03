/**
 * Smarter manifest helpers: parse the editor's YAML, and prepare it for the cli api.
 */
import { load } from "js-yaml";

export type ManifestDependency = {
  kind: string;
  name: string;
};

export type Manifest = {
  apiVersion: string;
  kind: string;
  metadata: { name: string; [key: string]: unknown };
  spec?: unknown;
  status?: { dependencies?: ManifestDependency[] | null; [key: string]: unknown } | null;
  [key: string]: unknown;
};

/**
 * Parse and validate a YAML manifest.
 *
 * @throws Error if the YAML is invalid, or is not a Smarter manifest.
 */
export function parseManifest(yaml: string): Manifest {
  const manifest = load(yaml) as Manifest;
  if (!manifest || typeof manifest !== "object") {
    throw new Error("The manifest is not a YAML object.");
  }
  if (!manifest.apiVersion?.startsWith?.("smarter.sh/v")) {
    throw new Error("The manifest's apiVersion is missing, or is not smarter.sh/v1.");
  }
  if (!manifest.kind) {
    throw new Error("The manifest's kind is missing.");
  }
  if (!manifest.metadata?.name) {
    throw new Error("The manifest's metadata.name is missing.");
  }
  return manifest;
}

/** Return the manifest without its status, which is read only, for the cli apply api. */
export function manifestToApply(manifest: Manifest): Manifest {
  const rest = { ...manifest };
  delete rest.status;
  return rest;
}

/** Return a copy of the manifest, renamed, for the cli apply api to create as a new resource. */
export function cloneManifest(manifest: Manifest, newName: string): Manifest {
  const clone = manifestToApply(manifest);
  return { ...clone, metadata: { ...clone.metadata, name: newName } };
}

/** Return the resources that depend on the manifest's resource, from its status. */
export function manifestDependencies(manifest: Manifest | null): ManifestDependency[] {
  return manifest?.status?.dependencies ?? [];
}
