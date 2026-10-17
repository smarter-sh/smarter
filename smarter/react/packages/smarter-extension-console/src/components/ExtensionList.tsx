/**
 * The Extensions list page: the installed extensions, and the registry's, which can be installed,
 * and an archive's upload. Superusers manage them; everyone else sees them read-only.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { gettext, interpolate, interpolateNodes, Modal, WorkbenchHelp } from "@smarter/common";

import { Documentation, Notice, Spinner, TrustBadge } from "@/components/common";
import type { NoticeState } from "@/components/common";
import * as api from "@/lib/api";
import { errorText } from "@/lib/api";
import type {
  ConsoleContext,
  ExtensionListResponse,
  ExtensionSummary,
  RegistryExtension,
  RegistryResponse,
} from "@/lib/types";

type Tab = "installed" | "browse";

const DOCS_URL = "https://docs.smarter.sh/en/latest/smarter-platform/extensions.html";
const HELP_TEXT = gettext(
  "Extensions are Python packages that add tools to the LLMs of this platform. Install them from the signed Smarter " +
    "Extension registry, or upload an archive, then configure and enable them. An extension's code runs with full " +
    "access to the platform: install only extensions whose publisher you trust.",
);

type Props = {
  context: ConsoleContext;
  /** Opens another page. Tests replace it. */
  navigate?: (url: string) => void;
};

export default function ExtensionList({ context, navigate = (url) => window.location.assign(url) }: Props) {
  const [tab, setTab] = useState<Tab>("installed");
  const [list, setList] = useState<ExtensionListResponse | null>(null);
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [notice, setNotice] = useState<NoticeState>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [details, setDetails] = useState<RegistryExtension | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  // state is set only in the promises' callbacks, once the api answers.
  const loadList = useCallback(
    () =>
      api
        .listExtensions(context)
        .then(setList)
        .catch((error: unknown) => setNotice({ kind: "danger", text: errorText(error) })),
    [context],
  );

  const fetchRegistry = useCallback(
    (refresh: boolean) =>
      api
        .getRegistry(context, refresh)
        .then(setRegistry)
        .catch((error: unknown) => setNotice({ kind: "danger", text: errorText(error) })),
    [context],
  );

  const refreshRegistry = () => {
    setBusy("registry");
    void fetchRegistry(true).finally(() => setBusy(null));
  };

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    if (tab === "browse" && registry === null) void fetchRegistry(false);
  }, [tab, registry, fetchRegistry]);

  /** Run an action, report its message, and reload the list. */
  const run = async (key: string, action: () => Promise<{ message: string }>, then?: () => void) => {
    setBusy(key);
    setNotice(null);
    try {
      const result = await action();
      setNotice({ kind: "success", text: result.message });
      await loadList();
      then?.();
    } catch (error) {
      setNotice({ kind: "danger", text: errorText(error) });
    } finally {
      setBusy(null);
    }
  };

  const toggle = (extension: ExtensionSummary) =>
    run(`toggle:${extension.slug}`, () =>
      extension.enabled ? api.disable(context, extension.slug) : api.enable(context, extension.slug),
    );

  const installFromRegistry = async (entry: RegistryExtension, version?: string | null) => {
    setBusy(`install:${entry.slug}`);
    setNotice(null);
    try {
      const result = await api.install(context, entry.slug, version);
      setDetails(null);
      navigate(result.extension?.detailUrl ?? context.listUrl);
    } catch (error) {
      setNotice({ kind: "danger", text: errorText(error) });
      setBusy(null);
    }
  };

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setBusy("upload");
    setNotice(null);
    try {
      const result = await api.uploadArchive(context, file);
      navigate(result.extension?.detailUrl ?? context.listUrl);
    } catch (error) {
      setNotice({ kind: "danger", text: errorText(error) });
      setBusy(null);
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <section className="mt-5 mb-5 container" id="extension-list">
      <WorkbenchHelp title={gettext("Extensions")} icon="ki-abstract-26" docsUrl={DOCS_URL} helpText={HELP_TEXT} />
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-5">
        <ul className="nav nav-tabs nav-line-tabs fs-6 border-0" role="tablist">
          {(["installed", "browse"] as Tab[]).map((key) => (
            <li className="nav-item" key={key} role="presentation">
              <button
                type="button"
                role="tab"
                aria-selected={tab === key}
                className={`nav-link btn btn-link ${tab === key ? "active fw-bold" : ""}`}
                onClick={() => setTab(key)}
              >
                {key === "installed" ? gettext("Installed") : gettext("Browse the registry")}
                {key === "installed" && list ? (
                  <span className="badge badge-light ms-2">{list.objects.length}</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
        {context.canEdit ? (
          <div className="d-flex gap-2">
            <input
              ref={fileInput}
              type="file"
              accept=".zip,application/zip"
              className="d-none"
              aria-label={gettext("Extension archive")}
              onChange={(event) => void upload(event.target.files?.[0])}
            />
            <button
              type="button"
              className="btn btn-sm btn-light-primary"
              disabled={busy !== null}
              onClick={() => fileInput.current?.click()}
            >
              {busy === "upload" ? (
                <Spinner label={gettext("Uploading")} />
              ) : (
                <i className="ki-outline ki-file-up fs-4 me-1" />
              )}
              {gettext("Upload extension")}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-light"
              disabled={busy !== null || !list?.registryEnabled}
              title={
                list && !list.registryEnabled
                  ? gettext("The registry is disabled until its public key is set.")
                  : undefined
              }
              onClick={() => void run("check", () => api.checkUpdates(context))}
            >
              {busy === "check" ? (
                <Spinner label={gettext("Checking")} />
              ) : (
                <i className="ki-outline ki-arrows-circle fs-4 me-1" />
              )}
              {gettext("Check for updates")}
            </button>
          </div>
        ) : null}
      </div>

      {tab === "installed" ? (
        <InstalledTable
          list={list}
          busy={busy}
          canEdit={context.canEdit}
          onToggle={(extension) => void toggle(extension)}
        />
      ) : (
        <RegistryGrid
          registry={registry}
          busy={busy}
          canEdit={context.canEdit}
          onRefresh={refreshRegistry}
          onInstall={(entry) => void installFromRegistry(entry)}
          onDetails={setDetails}
        />
      )}

      <RegistryDetails
        key={details?.slug ?? ""}
        entry={details}
        busy={busy}
        canEdit={context.canEdit}
        onClose={() => setDetails(null)}
        onInstall={(entry, version) => void installFromRegistry(entry, version)}
      />
    </section>
  );
}

/** The installed extensions. */
export function InstalledTable({
  list,
  busy,
  canEdit = true,
  onToggle,
}: {
  list: ExtensionListResponse | null;
  busy: string | null;
  /** Whether the enabled switches can be toggled. */
  canEdit?: boolean;
  onToggle: (extension: ExtensionSummary) => void;
}) {
  if (list === null) return <p className="text-muted">{gettext("Loading...")}</p>;
  if (list.objects.length === 0)
    return (
      <p className="text-muted">
        {canEdit
          ? gettext("No extensions are installed. Browse the registry, or upload an archive.")
          : gettext("No extensions are installed.")}
      </p>
    );
  return (
    <div className="table-responsive">
      <table className="table table-row-dashed align-middle gs-0 gy-3">
        <thead className="table-light">
          <tr className="fw-bold text-muted">
            <th>{gettext("Extension")}</th>
            <th>{gettext("Version")}</th>
            <th className="d-none d-md-table-cell">{gettext("Trust")}</th>
            <th className="d-none d-lg-table-cell">{gettext("Source")}</th>
            <th>{gettext("Enabled")}</th>
          </tr>
        </thead>
        <tbody>
          {list.objects.map((extension) => (
            <tr key={extension.slug}>
              <td>
                <a href={extension.detailUrl} className="fw-bold text-gray-800 text-hover-primary">
                  {extension.displayName}
                </a>
                {extension.error ? (
                  <i
                    className="ki-outline ki-information-5 text-danger fs-4 ms-2"
                    title={extension.error}
                    aria-label={gettext("Error")}
                  />
                ) : null}
                <div className="text-muted fs-7">{extension.description}</div>
              </td>
              <td>
                {extension.installedVersion}
                {extension.updateAvailable ? (
                  <span className="badge badge-light-warning ms-2">
                    {interpolateNodes(gettext("%(latestVersion)s available"), {
                      latestVersion: extension.latestVersion,
                    })}
                  </span>
                ) : null}
              </td>
              <td className="d-none d-md-table-cell">
                <TrustBadge badge={extension.trustBadge} label={extension.trustBadgeLabel} />
              </td>
              <td className="d-none d-lg-table-cell text-capitalize">{extension.source}</td>
              <td>
                <div className="form-check form-switch">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    role="switch"
                    checked={extension.enabled}
                    disabled={busy !== null || !canEdit}
                    aria-label={interpolate(gettext("Enable %(displayName)s"), { displayName: extension.displayName })}
                    onChange={() => onToggle(extension)}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const BADGE_FILTERS = [
  { value: "", label: gettext("Any publisher") },
  { value: "official", label: gettext("Official Smarter Extensions") },
  { value: "verified", label: gettext("Verified Publishers") },
  { value: "community", label: gettext("Community") },
];

/** The registry's extensions, as cards, with a search and a badge filter. */
export function RegistryGrid({
  registry,
  busy,
  canEdit = true,
  onRefresh,
  onInstall,
  onDetails,
}: {
  registry: RegistryResponse | null;
  busy: string | null;
  /** Whether the registry can be refreshed, and its extensions installed. */
  canEdit?: boolean;
  onRefresh: () => void;
  onInstall: (entry: RegistryExtension) => void;
  onDetails: (entry: RegistryExtension) => void;
}) {
  const [query, setQuery] = useState("");
  const [badge, setBadge] = useState("");
  const entries = useMemo(() => {
    const text = query.trim().toLowerCase();
    return (registry?.objects ?? []).filter(
      (entry) =>
        (!badge || entry.trustBadge === badge) &&
        (!text ||
          [entry.slug, entry.displayName, entry.description, entry.publisher].join(" ").toLowerCase().includes(text)),
    );
  }, [registry, query, badge]);

  if (registry === null) return <p className="text-muted">{gettext("Loading the registry...")}</p>;
  if (registry.error) return <div className="alert alert-warning">{registry.error}</div>;
  return (
    <>
      <div className="d-flex flex-wrap gap-3 mb-5">
        <input
          type="search"
          className="form-control form-control-sm"
          style={{ maxWidth: 320 }}
          placeholder={gettext("Search extensions")}
          aria-label={gettext("Search extensions")}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select
          className="form-select form-select-sm"
          style={{ maxWidth: 260 }}
          aria-label={gettext("Publisher")}
          value={badge}
          onChange={(event) => setBadge(event.target.value)}
        >
          {BADGE_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {canEdit ? (
          <button type="button" className="btn btn-sm btn-light" disabled={busy !== null} onClick={onRefresh}>
            {busy === "registry" ? <Spinner label={gettext("Refreshing")} /> : null}
            {gettext("Refresh")}
          </button>
        ) : null}
      </div>
      {entries.length === 0 ? (
        <p className="text-muted">{gettext("No extensions match.")}</p>
      ) : (
        <div className="row g-5">
          {entries.map((entry) => (
            <div className="col-md-6 col-xl-4" key={entry.slug}>
              <RegistryCard entry={entry} busy={busy} canEdit={canEdit} onInstall={onInstall} onDetails={onDetails} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}

/** A registry extension's card, with what it offers on this platform. */
function RegistryCard({
  entry,
  busy,
  canEdit,
  onInstall,
  onDetails,
}: {
  entry: RegistryExtension;
  busy: string | null;
  canEdit: boolean;
  onInstall: (entry: RegistryExtension) => void;
  onDetails: (entry: RegistryExtension) => void;
}) {
  const installing = busy === `install:${entry.slug}`;
  return (
    <article className="card card-bordered h-100" aria-label={entry.displayName}>
      <div className="card-body d-flex flex-column">
        <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
          <h3 className="fs-5 fw-bold mb-0">{entry.displayName}</h3>
          <TrustBadge badge={entry.trustBadge} label={entry.trustBadgeLabel} />
        </div>
        <p className="text-gray-700 flex-grow-1">{entry.description}</p>
        <p className="text-muted fs-7 mb-4">
          {gettext("By")}{" "}
          {entry.publisherUrl ? (
            <a href={entry.publisherUrl} target="_blank" rel="noopener noreferrer">
              {entry.publisher}
            </a>
          ) : (
            entry.publisher
          )}
          {entry.license ? ` · ${entry.license}` : ""}
        </p>
        <div className="d-flex gap-2 align-items-center">
          {canEdit && (entry.action === "install" || entry.action === "update") ? (
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={busy !== null}
              onClick={() => onInstall(entry)}
            >
              {installing ? <Spinner label={gettext("Installing")} /> : null}
              {entry.action === "install"
                ? interpolate(gettext("Install %(latestVersion)s"), { latestVersion: entry.latestVersion })
                : interpolate(gettext("Update to %(latestVersion)s"), { latestVersion: entry.latestVersion })}
            </button>
          ) : null}
          {entry.action === "installed" && entry.detailUrl ? (
            <a className="btn btn-sm btn-light-success" href={entry.detailUrl}>
              {interpolateNodes(gettext("Installed (%(installedVersion)s)"), {
                installedVersion: entry.installedVersion,
              })}
            </a>
          ) : null}
          {entry.action === "uploaded" ? (
            <span className="text-muted fs-7">{gettext("Installed from an uploaded archive")}</span>
          ) : null}
          {entry.action === "incompatible" ? (
            <span className="text-muted fs-7">{gettext("Not compatible with this version of Smarter")}</span>
          ) : null}
          <button type="button" className="btn btn-sm btn-link ms-auto" onClick={() => onDetails(entry)}>
            {gettext("Details")}
          </button>
        </div>
      </div>
    </article>
  );
}

/** A registry extension's documentation and versions, before it is installed. */
function RegistryDetails({
  entry,
  busy,
  canEdit,
  onClose,
  onInstall,
}: {
  entry: RegistryExtension | null;
  busy: string | null;
  canEdit: boolean;
  onClose: () => void;
  onInstall: (entry: RegistryExtension, version: string) => void;
}) {
  const compatible = entry?.versions.filter((version) => version.compatible) ?? [];
  // the dialog is keyed by its extension, so its version starts as the extension's newest.
  const [version, setVersion] = useState(entry?.latestVersion ?? "");
  if (!entry) return null;
  const canInstall = canEdit && entry.action !== "uploaded" && compatible.length > 0;
  return (
    <Modal show={true} title={entry.displayName} onClose={onClose}>
      <div className="mb-4">
        <TrustBadge badge={entry.trustBadge} label={entry.trustBadgeLabel} />{" "}
        <span className="text-muted fs-7">
          {interpolateNodes(gettext("By %(publisher)s"), { publisher: entry.publisher })}
          {entry.license ? ` · ${entry.license}` : ""}
          {entry.homepage ? (
            <>
              {" · "}
              <a href={entry.homepage} target="_blank" rel="noopener noreferrer">
                {gettext("homepage")}
              </a>
            </>
          ) : null}
        </span>
      </div>
      {canInstall ? (
        <div className="d-flex gap-2 mb-5">
          <select
            className="form-select form-select-sm"
            style={{ maxWidth: 160 }}
            aria-label={gettext("Version")}
            value={version}
            onChange={(event) => setVersion(event.target.value)}
          >
            {compatible.map((item) => (
              <option key={item.version} value={item.version}>
                {item.version}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-sm btn-primary"
            disabled={busy !== null || !version}
            onClick={() => onInstall(entry, version)}
          >
            {busy === `install:${entry.slug}` ? <Spinner label={gettext("Installing")} /> : null}
            {entry.installedVersion ? gettext("Install this version") : gettext("Install")}
          </button>
        </div>
      ) : null}
      <Documentation html={entry.docsHtml} />
    </Modal>
  );
}
