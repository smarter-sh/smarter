/**
 * ResourceDetail React Component
 *
 * The detail of one resource of a list, in a dialog that opens when a row of the list is chosen (see
 * TabbedListView). Its tabs:
 *
 * - Details: the list's own DetailView of the object, built from DetailSection and DetailField.
 * - Manifest: the resource's manifest, as YAML, with Copy, Download and Edit manifest.
 * - Hierarchy: the tree of the resources that it uses, recursively, as in the Prompt Engineer's Workbench's
 *   Architecture tab.
 * - Dependencies: the resources that use it, which keep it from being deleted.
 *
 * The last three are fetched once, from the object's detailUrl, when the object is shown. An object without a
 * detailUrl, e.g. an Extension, has the Details tab only.
 *
 * Its header has the resource's kind and name, its position in the list, and buttons that show the previous and
 * next resources of the list, which the arrow keys press too. The tab that is open stays open from one resource to
 * the next, so that their manifests, say, can be compared. Escape, the close button, and a click outside the dialog
 * close it.
 *
 * Usage:
 * <ResourceDetail
 *   sessionContext={sessionContext}
 *   object={guardrail}
 *   objectTypeName="guardrail"
 *   DetailView={GuardrailDetailView}
 *   position={{ index: 3, count: 25 }}
 *   onPrevious={...}
 *   onNext={...}
 *   onClose={...}
 *   onRequery={onRequery}
 * />
 */
import { useEffect, useId, useRef, useState } from "react";
import type { ComponentType, KeyboardEvent as ReactKeyboardEvent } from "react";

import type { DetailObject, DetailViewBaseProps, Filtering, SessionContext } from "../../lib/Types";
import { gettext, interpolate } from "../../lib/i18n";
import { Loading } from "../Loading";
import { kindInfo } from "../ResourceTree/kinds";
import { countResources } from "../ResourceTree/tree";
import { fetchResourceDetail, type ResourceDetailData } from "./api";
import { DependenciesTab, HierarchyTab, ManifestTab } from "./tabs";
import "./styles.css";

/** The tabs of the detail. */
export type ResourceDetailTab = "details" | "manifest" | "hierarchy" | "dependencies";

export interface ResourceDetailProps {
  sessionContext: SessionContext;
  /** The list's object: its name and detailUrl are read here, and its DetailView shows the rest. */
  object: unknown;
  /** The name of the list's object type, e.g. "guardrail", until the detail says the resource's kind. */
  objectTypeName: string;
  /** The Details tab. */
  DetailView: ComponentType<DetailViewBaseProps<unknown, SessionContext>>;
  onRequery: () => void;
  filtering?: Filtering;
  /** The object's position in the whole list, from 1, and how many objects the list has. */
  position?: { index: number; count: number };
  /** Shows the previous object. Without it, the Previous button is disabled. */
  onPrevious?: () => void;
  /** Shows the next object. Without it, the Next button is disabled. */
  onNext?: () => void;
  /** Whether the next or previous object is loading, e.g. from another page of the list. */
  isNavigating?: boolean;
  onClose: () => void;
}

/** The last response of the detail api, keyed by the url and the attempt that requested it. */
type Fetched = { key: string } & ({ data: ResourceDetailData } | { message: string });

type DetailState =
  | { status: "none" }
  | { status: "loading" }
  | { status: "loaded"; data: ResourceDetailData }
  | { status: "error"; message: string };

/** Whether a key press is typing, which the arrow keys must not interrupt. */
function isTyping(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/** The kind as a title, e.g. "Guardrail", from a list's object type name, e.g. "guardrail". */
const titleCase = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

export default function ResourceDetail({
  sessionContext,
  object,
  objectTypeName,
  DetailView,
  onRequery,
  filtering,
  position,
  onPrevious,
  onNext,
  isNavigating = false,
  onClose,
}: ResourceDetailProps) {
  const titleId = useId();
  const tabsId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const { name: ownName, displayName, title: ownTitle, slug, detailUrl } = (object ?? {}) as DetailObject;
  // an object that has no name, e.g. an Extension, is called by its display name, title or slug.
  const name = ownName ?? displayName ?? ownTitle ?? slug;
  const [activeTab, setActiveTab] = useState<ResourceDetailTab>("details");
  const [fetched, setFetched] = useState<Fetched | null>(null);
  const [reloads, setReloads] = useState(0);

  // fetch the manifest, hierarchy and dependencies of each resource that is shown. A response is kept with the url
  // and attempt that requested it, so that a resource whose response hasn't come yet is loading.
  const fetchKey = detailUrl ? `${reloads}:${detailUrl}` : "";
  useEffect(() => {
    if (!detailUrl) return;
    let current = true;
    fetchResourceDetail(sessionContext, detailUrl)
      .then((data) => current && setFetched({ key: fetchKey, data }))
      .catch((error: Error) => current && setFetched({ key: fetchKey, message: error.message }));
    return () => {
      current = false;
    };
  }, [sessionContext, detailUrl, fetchKey]);
  const detail: DetailState = !detailUrl
    ? { status: "none" }
    : fetched?.key !== fetchKey
      ? { status: "loading" }
      : "data" in fetched
        ? { status: "loaded", data: fetched.data }
        : { status: "error", message: fetched.message };

  // an object without a detail has the Details tab only.
  const tab: ResourceDetailTab = detailUrl ? activeTab : "details";

  // the dialog has the focus while it is open, and gives it back to the row that opened it when it closes.
  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.focus();
    document.body.classList.add("modal-open");
    return () => {
      document.body.classList.remove("modal-open");
      opener?.focus?.();
    };
  }, []);

  // Escape closes the dialog, and the arrow keys show the previous and next resources, unless the user is typing,
  // or a dialog of the detail's own, e.g. a Toolbar's Rename, has the key.
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target instanceof Element ? e.target : null;
      const dialog = target?.closest('[role="dialog"]');
      if (dialog && dialog !== dialogRef.current) return;
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowLeft" && onPrevious && !isTyping(e.target) && !isNavigating) {
        e.preventDefault();
        onPrevious();
      } else if (e.key === "ArrowRight" && onNext && !isTyping(e.target) && !isNavigating) {
        e.preventDefault();
        onNext();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, onPrevious, onNext, isNavigating]);

  const data = detail.status === "loaded" ? detail.data : null;
  const kind = data?.kind ?? titleCase(objectTypeName);
  const info = kindInfo(kind);
  const icon = data?.tree.icon ?? "abstract-26";
  const owner = data?.tree.owner;
  const title = name ?? data?.name ?? kind;

  const tabs: { key: ResourceDetailTab; label: string; icon: string; count?: number }[] = [
    { key: "details", label: gettext("Details"), icon: "information-4" },
  ];
  if (detailUrl) {
    tabs.push(
      { key: "manifest", label: gettext("Manifest"), icon: "code" },
      {
        key: "hierarchy",
        label: gettext("Hierarchy"),
        icon: "data",
        count: data ? countResources(data.tree) - 1 : undefined,
      },
      { key: "dependencies", label: gettext("Dependencies"), icon: "fasten", count: data?.dependents.length },
    );
  }

  // the tab list's arrow keys move between its tabs, as a tab list's should, rather than between resources.
  const onTabKeyDown = (e: ReactKeyboardEvent<HTMLButtonElement>, index: number) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    e.stopPropagation();
    e.nativeEvent.stopImmediatePropagation();
    const next = (index + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    setActiveTab(tabs[next].key);
    document.getElementById(`${tabsId}-${tabs[next].key}`)?.focus();
  };

  // a tag or annotation that is clicked narrows the list, which the dialog would hide.
  const detailFiltering: Filtering | undefined = filtering && {
    ...filtering,
    onTag: (value) => {
      onClose();
      filtering.onTag(value);
    },
    onAnnotation: (value) => {
      onClose();
      filtering.onAnnotation(value);
    },
  };

  const remote = (render: (loaded: ResourceDetailData) => React.ReactNode) => {
    if (detail.status === "loaded") return render(detail.data);
    if (detail.status === "error") {
      return (
        <div className="alert alert-danger d-flex align-items-center gap-3" role="alert">
          <i className="ki-outline ki-information-5 fs-2 text-danger" aria-hidden="true" />
          <span className="me-auto">
            {interpolate(gettext("The detail of %(name)s could not be loaded: %(error)s"), {
              name: title,
              error: detail.message,
            })}
          </span>
          <button type="button" className="btn btn-sm btn-light-danger" onClick={() => setReloads((n) => n + 1)}>
            {gettext("Try again")}
          </button>
        </div>
      );
    }
    return (
      <div className="smarter-detail-loading">
        <Loading />
      </div>
    );
  };

  return (
    // Clicking outside the dialog closes it: a mouse convenience, whose keyboard equivalent is Escape.
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div className="smarter-detail-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="smarter-detail-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        ref={dialogRef}
        tabIndex={-1}
      >
        <header className="smarter-detail-header">
          <span className={`smarter-detail-kind-icon bg-light-${info.tone} text-${info.tone}`} aria-hidden="true">
            <i className={`ki-outline ki-${icon}`} />
          </span>
          <div className="smarter-detail-heading">
            <div className="smarter-detail-eyebrow">
              {/* the kind is a product term, e.g. SqlPlugin, which isn't translated. */}
              <span className={`text-${info.tone}`}>{kind}</span>
              {owner && (
                <>
                  <span aria-hidden="true">·</span>
                  <span className="text-truncate">
                    <i className="ki-outline ki-profile-circle fs-7 me-1" aria-hidden="true" />
                    {owner}
                  </span>
                </>
              )}
            </div>
            <h2 id={titleId} className="smarter-detail-title">
              {title}
            </h2>
          </div>
          <nav className="smarter-detail-pager" aria-label={gettext("Browse the list")}>
            {isNavigating && (
              <span className="spinner-border spinner-border-sm text-primary" role="status">
                <span className="visually-hidden">{gettext("Loading...")}</span>
              </span>
            )}
            <button
              type="button"
              className="btn btn-icon btn-sm btn-light"
              onClick={onPrevious}
              disabled={!onPrevious || isNavigating}
              title={gettext("Previous (←)")}
              aria-label={gettext("Previous")}
            >
              <i className="ki-outline ki-left fs-4" aria-hidden="true" />
            </button>
            {position && (
              <span className="smarter-detail-position" aria-live="polite">
                {interpolate(gettext("%(index)s of %(count)s"), {
                  index: position.index.toLocaleString(),
                  count: position.count.toLocaleString(),
                })}
              </span>
            )}
            <button
              type="button"
              className="btn btn-icon btn-sm btn-light"
              onClick={onNext}
              disabled={!onNext || isNavigating}
              title={gettext("Next (→)")}
              aria-label={gettext("Next")}
            >
              <i className="ki-outline ki-right fs-4" aria-hidden="true" />
            </button>
            <span className="smarter-detail-divider" aria-hidden="true" />
            <button
              type="button"
              className="btn btn-icon btn-sm btn-light"
              onClick={onClose}
              title={gettext("Close (Esc)")}
              aria-label={gettext("Close")}
            >
              <i className="ki-outline ki-cross fs-2" aria-hidden="true" />
            </button>
          </nav>
        </header>

        <div className="smarter-detail-tabs" role="tablist" aria-label={gettext("Detail")}>
          {tabs.map((item, index) => (
            <button
              key={item.key}
              id={`${tabsId}-${item.key}`}
              type="button"
              role="tab"
              aria-selected={tab === item.key}
              aria-controls={`${tabsId}-panel`}
              tabIndex={tab === item.key ? 0 : -1}
              className={`smarter-detail-tab${tab === item.key ? " active" : ""}`}
              onClick={() => setActiveTab(item.key)}
              onKeyDown={(e) => onTabKeyDown(e, index)}
            >
              <i className={`ki-outline ki-${item.icon} fs-5`} aria-hidden="true" />
              {item.label}
              {item.count !== undefined && <span className="smarter-detail-tab-count">{item.count}</span>}
            </button>
          ))}
        </div>

        <div
          className="smarter-detail-body"
          id={`${tabsId}-panel`}
          role="tabpanel"
          aria-labelledby={`${tabsId}-${tab}`}
        >
          {tab === "details" && (
            <div className="smarter-detail-details">
              <DetailView
                sessionContext={sessionContext}
                object={object}
                onRequery={onRequery}
                filtering={detailFiltering}
              />
            </div>
          )}
          {tab === "manifest" && remote((loaded) => <ManifestTab key={loaded.recordLocator} detail={loaded} />)}
          {tab === "hierarchy" && remote((loaded) => <HierarchyTab key={loaded.recordLocator} detail={loaded} />)}
          {tab === "dependencies" && remote((loaded) => <DependenciesTab detail={loaded} />)}
        </div>
      </div>
    </div>
  );
}
