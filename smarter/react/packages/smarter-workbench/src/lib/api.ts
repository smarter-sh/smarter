/**
 * The workbench's own requests: the data of the Console's Manifest, Architecture and Deployment tabs, which they
 * fetch when they are first opened. See
 * smarter.apps.prompt.views.detailviews.prompt_manifest_view.LLMClientManifestEditorView,
 * prompt_architecture_view.LLMClientArchitectureView and prompt_deployment_view.LLMClientDeploymentView.
 */
import { gettext, interpolate } from "@smarter/common";
import type { SAMDependencyTreeNode } from "@smarter/llmclient-architecture";
import type { LLMClientDeploymentPage } from "@smarter/llmclient-deployment";

/** A failed request: its message, for the person who opened the tab. */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** GET a url of the workbench's own origin, with the user's session, and return its JSON. */
async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new ApiError(
      interpolate(gettext("The request failed: %(status)s %(statusText)s"), {
        status: response.status,
        statusText: response.statusText,
      }).trim(),
      response.status,
    );
  }
  return (await response.json()) as T;
}

/** The LLMClient's manifest, as YAML. */
export async function fetchManifest(url: string): Promise<string> {
  const { manifest } = await getJson<{ manifest: string }>(url);
  return manifest;
}

/** The LLMClient's architecture: the tree of the SAM resources that it is built from. */
export const fetchArchitecture = (url: string) => getJson<SAMDependencyTreeNode>(url);

/** The LLMClient's deployment page, as the workbench shows it: with its owner and api keys. */
export const fetchDeploymentPage = (url: string) => getJson<LLMClientDeploymentPage>(url);
