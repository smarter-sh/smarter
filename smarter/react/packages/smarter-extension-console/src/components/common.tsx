/**
 * Small components that both of the Extensions pages use.
 */
import type { ReactNode } from "react";
import { gettext } from "@smarter/common";

/** The Bootstrap badge color of each trust badge. */
const BADGE_CLASSES: Record<string, string> = {
  official: "badge-light-success",
  verified: "badge-light-primary",
  community: "badge-light-secondary",
  unverified: "badge-light-warning",
};

/** A publisher's trust badge, e.g. "Official Smarter Extension". */
export function TrustBadge({ badge, label }: { badge: string; label: string }) {
  return (
    <span
      className={`badge ${BADGE_CLASSES[badge] ?? "badge-light-secondary"}`}
      title={gettext("The publisher's trust badge")}
    >
      {label}
    </span>
  );
}

/** What an action did, or why it failed. */
export type NoticeState = { kind: "success" | "danger" | "warning" | "info"; text: string } | null;

/** A dismissible alert. */
export function Notice({ notice, onClose }: { notice: NoticeState; onClose: () => void }) {
  if (!notice) return null;
  return (
    <div className={`alert alert-${notice.kind} d-flex align-items-start justify-content-between`} role="alert">
      <span>{notice.text}</span>
      <button type="button" className="btn-close ms-4" aria-label={gettext("Dismiss")} onClick={onClose} />
    </div>
  );
}

/** A spinner, inside a button whose action is running. */
export function Spinner({ label = gettext("Working") }: { label?: string }) {
  return <span className="spinner-border spinner-border-sm me-2" role="status" aria-label={label} />;
}

/**
 * An extension's documentation, which the backend renders as HTML from reStructuredText, with raw
 * HTML and file inclusion disabled (smarter.apps.llmtool.extension.docs), so it is safe to insert.
 */
export function Documentation({
  html,
  empty = gettext("This extension has no documentation."),
}: {
  html: string;
  empty?: string;
}) {
  if (!html.trim()) return <p className="text-muted">{empty}</p>;
  return <div className="smarter-extension-docs" dangerouslySetInnerHTML={{ __html: html }} />;
}

/** A labeled value, in a definition list. */
export function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="col-sm-3 text-muted fw-semibold">{label}</dt>
      <dd className="col-sm-9">{children}</dd>
    </>
  );
}
