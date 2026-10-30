/**
 * Labels and badges of a Vectorstore's fields, shared by the ListView, DetailView and StatusBar.
 */
import type { Vectorstore, VectorstoreStatus } from "@/lib/Types";
import { gettext } from "@smarter/common";

export const BACKEND_LABELS: Record<Vectorstore["backend"], string> = {
  qdrant: "Qdrant",
  pinecone: "Pinecone",
};

export const HOSTING_LABELS: Record<Vectorstore["hosting"], string> = {
  self_hosted: gettext("Self-hosted"),
  managed: gettext("Managed"),
};

export const STATUS_BADGES: Record<VectorstoreStatus, { className: string; label: string; help: string }> = {
  pending: {
    className: "badge-light",
    label: gettext("Pending"),
    help: gettext("Applied, but not deployed. Deploy it to create its database."),
  },
  provisioning: {
    className: "badge-light-warning",
    label: gettext("Provisioning"),
    help: gettext("Its database is being created."),
  },
  ready: { className: "badge-light-success", label: gettext("Ready"), help: gettext("Its database is serving.") },
  stopped: {
    className: "badge-light-secondary",
    label: gettext("Stopped"),
    help: gettext("Undeployed. Its data is kept."),
  },
  failed: { className: "badge-light-danger", label: gettext("Failed"), help: gettext("See its status message.") },
  deleting: {
    className: "badge-light-warning",
    label: gettext("Deleting"),
    help: gettext("Its database is being destroyed."),
  },
};

export function databaseLabel(vectorstore: Vectorstore): string {
  return `${BACKEND_LABELS[vectorstore.backend] ?? vectorstore.backend} · ${HOSTING_LABELS[vectorstore.hosting] ?? vectorstore.hosting}`;
}

export function formatCount(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString();
}
