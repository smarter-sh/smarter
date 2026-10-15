/**
 * An extension's page: its documentation, tools, settings, availability, versions and resources,
 * and every action on it. For superusers.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import { formatDateTime } from "@smarter/common";

import { Documentation, Fact, Notice, Spinner, TrustBadge } from "@/components/common";
import type { NoticeState } from "@/components/common";
import SettingsForm from "@/components/SettingsForm";
import * as api from "@/lib/api";
import { errorText } from "@/lib/api";
import type { AccountRef, ActionResponse, ConsoleContext, ExtensionDetail } from "@/lib/types";

type Tab = "overview" | "tools" | "settings" | "availability" | "versions" | "resources";

const TABS: { key: Tab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "tools", label: "Tools" },
  { key: "settings", label: "Settings" },
  { key: "availability", label: "Availability" },
  { key: "versions", label: "Versions" },
  { key: "resources", label: "Resources" },
];

type Props = {
  context: ConsoleContext;
  slug: string;
  /** Opens another page. Tests replace it. */
  navigate?: (url: string) => void;
  /** Asks the person to confirm a destructive action. Tests replace it. */
  confirm?: (message: string) => boolean;
};

export default function ExtensionPage({
  context,
  slug,
  navigate = (url) => window.location.assign(url),
  confirm = (message) => window.confirm(message),
}: Props) {
  const [extension, setExtension] = useState<ExtensionDetail | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [notice, setNotice] = useState<NoticeState>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  // state is set only in the promise's callbacks, once the api answers.
  const load = useCallback(
    () =>
      api
        .getExtension(context, slug)
        .then((response) => setExtension(response.extension))
        .catch((error: unknown) => {
          setLoadFailed(true);
          setNotice({ kind: "danger", text: errorText(error) });
        }),
    [context, slug],
  );

  useEffect(() => {
    void load();
  }, [load]);

  /** Run an action, report its message, and show the extension as it now is. */
  const run = async (key: string, action: () => Promise<ActionResponse>) => {
    setBusy(key);
    setNotice(null);
    try {
      const result = await action();
      setNotice({ kind: "success", text: result.message });
      if (result.extension) setExtension(result.extension);
      return result;
    } catch (error) {
      setNotice({ kind: "danger", text: errorText(error) });
      return null;
    } finally {
      setBusy(null);
    }
  };

  const uninstall = async () => {
    if (!extension) return;
    const question = `Uninstall ${extension.displayName}? Its settings, versions, waffle switches and the resources it created are deleted, and every LLMClient that lists it stops offering its tools.`;
    if (!confirm(question)) return;
    const result = await run("uninstall", () => api.uninstall(context, slug));
    if (result) navigate(context.listUrl);
  };

  if (extension === null) {
    return (
      <section className="mt-5 mb-5 container" id="extension-page">
        <Notice notice={notice} onClose={() => setNotice(null)} />
        {loadFailed ? <a href={context.listUrl}>Back to Extensions</a> : <p className="text-muted">Loading...</p>}
      </section>
    );
  }

  return (
    <section className="mt-5 mb-5 container" id="extension-page">
      <a href={context.listUrl} className="text-muted fs-7">
        <i className="ki-outline ki-arrow-left fs-6 me-1" />
        Extensions
      </a>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mt-3 mb-5">
        <div>
          <h1 className="fs-2 fw-bold mb-1">{extension.displayName}</h1>
          <div className="d-flex flex-wrap align-items-center gap-2 text-muted">
            <span>{extension.installedVersion ? `Version ${extension.installedVersion}` : "Not installed"}</span>
            <TrustBadge badge={extension.trustBadge} label={extension.trustBadgeLabel} />
            <span className={`badge ${extension.enabled ? "badge-light-success" : "badge-light"}`}>
              {extension.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
        </div>
        <button
          type="button"
          className={`btn btn-sm ${extension.enabled ? "btn-light" : "btn-primary"}`}
          disabled={busy !== null || (!extension.enabled && extension.missingSettings.length > 0)}
          title={
            !extension.enabled && extension.missingSettings.length > 0
              ? `Configure ${extension.missingSettings.join(", ")} first.`
              : undefined
          }
          onClick={() =>
            void run("toggle", () => (extension.enabled ? api.disable(context, slug) : api.enable(context, slug)))
          }
        >
          {busy === "toggle" ? <Spinner /> : null}
          {extension.enabled ? "Disable" : "Enable"}
        </button>
      </div>

      <Notice notice={notice} onClose={() => setNotice(null)} />
      {extension.updateAvailable ? (
        <div className="alert alert-warning d-flex flex-wrap align-items-center justify-content-between gap-3">
          <span>
            Version {extension.latestVersion} of {extension.displayName} is available. You have{" "}
            {extension.installedVersion}.
          </span>
          <button
            type="button"
            className="btn btn-sm btn-warning"
            disabled={busy !== null}
            onClick={() => void run("update", () => api.update(context, slug))}
          >
            {busy === "update" ? <Spinner label="Updating" /> : null}
            Update to {extension.latestVersion}
          </button>
        </div>
      ) : null}
      {extension.error ? <div className="alert alert-danger">{extension.error}</div> : null}
      {extension.loadError ? (
        <div className="alert alert-danger">The extension's code does not load: {extension.loadError}</div>
      ) : null}
      {!extension.enabled && extension.missingSettings.length > 0 ? (
        <div className="alert alert-info">
          Configure {extension.missingSettings.join(", ")} on the Settings tab, then enable the extension.
        </div>
      ) : null}

      <ul className="nav nav-tabs nav-line-tabs fs-6 mb-6" role="tablist">
        {TABS.map(({ key, label }) => (
          <li className="nav-item" key={key} role="presentation">
            <button
              type="button"
              role="tab"
              aria-selected={tab === key}
              className={`nav-link btn btn-link ${tab === key ? "active fw-bold" : ""}`}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          </li>
        ))}
      </ul>

      {tab === "overview" ? <Overview extension={extension} /> : null}
      {tab === "tools" ? <Tools extension={extension} /> : null}
      {tab === "settings" ? (
        <SettingsForm
          key={JSON.stringify(extension.settings)}
          extension={extension}
          busy={busy === "configure"}
          onSave={(request) => void run("configure", () => api.configure(context, slug, request))}
        />
      ) : null}
      {tab === "availability" ? (
        <Availability
          key={`${extension.allAccounts}:${extension.accounts.map((account) => account.id).join(",")}`}
          context={context}
          extension={extension}
          busy={busy === "availability"}
          onSave={(allAccounts, accountIds) =>
            void run("availability", () => api.setAvailability(context, slug, { allAccounts, accountIds }))
          }
        />
      ) : null}
      {tab === "versions" ? (
        <Versions
          extension={extension}
          busy={busy}
          onRollback={(versionId, version) => {
            if (confirm(`Roll ${extension.displayName} back to version ${version}?`))
              void run(`rollback:${versionId}`, () => api.rollback(context, slug, versionId));
          }}
        />
      ) : null}
      {tab === "resources" ? <Resources extension={extension} /> : null}

      <div className="card card-bordered border-danger mt-10">
        <div className="card-body d-flex flex-wrap align-items-center justify-content-between gap-3">
          <div>
            <h2 className="fs-5 fw-bold text-danger mb-1">Uninstall</h2>
            <p className="text-muted mb-0">
              Deletes the extension, its settings and versions, and the waffle switches and resources it created.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-danger"
            disabled={busy !== null}
            onClick={() => void uninstall()}
          >
            {busy === "uninstall" ? <Spinner label="Uninstalling" /> : null}
            Uninstall {extension.displayName}
          </button>
        </div>
      </div>
    </section>
  );
}

/** The extension's documentation, and what is known about it. */
function Overview({ extension }: { extension: ExtensionDetail }) {
  return (
    <>
      <dl className="row mb-8">
        <Fact label="Slug">
          <code>{extension.slug}</code>
        </Fact>
        <Fact label="Publisher">{extension.publisher || "Unknown"}</Fact>
        <Fact label="Source">
          {extension.source === "registry" ? "The Smarter Extension registry" : "An uploaded archive"}
        </Fact>
        {extension.license ? <Fact label="License">{extension.license}</Fact> : null}
        {extension.homepage ? (
          <Fact label="Homepage">
            <a href={extension.homepage} target="_blank" rel="noopener noreferrer">
              {extension.homepage}
            </a>
          </Fact>
        ) : null}
        {extension.latestCheckedAt ? (
          <Fact label="Updates checked">{formatDateTime(extension.latestCheckedAt, "date")}</Fact>
        ) : null}
      </dl>
      <Documentation html={extension.docsHtml} />
    </>
  );
}

/** The extension's tools, as the LLM sees them. */
function Tools({ extension }: { extension: ExtensionDetail }) {
  if (extension.tools.length === 0)
    return (
      <p className="text-muted">
        {extension.loadError ? "The tools can't be listed." : "This extension has no tools."}
      </p>
    );
  return (
    <div className="d-flex flex-column gap-5">
      {extension.tools.map((tool) => (
        <div className="card card-bordered" key={tool.name}>
          <div className="card-body">
            <h3 className="fs-5 fw-bold mb-1">
              <code>{tool.functionName}</code>
            </h3>
            <p className="text-gray-700">{tool.description}</p>
            <details>
              <summary className="text-primary">Parameters</summary>
              <pre className="bg-light p-4 rounded mt-2 fs-7">{JSON.stringify(tool.parameters, null, 2)}</pre>
            </details>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Which accounts may use the extension. */
function Availability({
  context,
  extension,
  busy,
  onSave,
}: {
  context: ConsoleContext;
  extension: ExtensionDetail;
  busy: boolean;
  onSave: (allAccounts: boolean, accountIds: number[]) => void;
}) {
  const [allAccounts, setAllAccounts] = useState(extension.allAccounts);
  const [selected, setSelected] = useState<Set<number>>(new Set(extension.accounts.map((account) => account.id)));
  const [accounts, setAccounts] = useState<AccountRef[] | null>(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (allAccounts || accounts !== null) return;
    api
      .getAccounts(context)
      .then((response) => setAccounts(response.objects))
      .catch((caught) => setError(errorText(caught)));
  }, [allAccounts, accounts, context]);

  const shown = useMemo(() => {
    const text = filter.trim().toLowerCase();
    return (accounts ?? []).filter(
      (account) => !text || `${account.accountNumber} ${account.companyName}`.toLowerCase().includes(text),
    );
  }, [accounts, filter]);

  const toggle = (id: number) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSave(allAccounts, allAccounts ? [] : [...selected]);
      }}
    >
      <div className="form-check mb-3">
        <input
          id="availability-all"
          className="form-check-input"
          type="radio"
          name="availability"
          checked={allAccounts}
          onChange={() => setAllAccounts(true)}
        />
        <label className="form-check-label" htmlFor="availability-all">
          Every account may use it
        </label>
      </div>
      <div className="form-check mb-5">
        <input
          id="availability-some"
          className="form-check-input"
          type="radio"
          name="availability"
          checked={!allAccounts}
          onChange={() => setAllAccounts(false)}
        />
        <label className="form-check-label" htmlFor="availability-some">
          Only these accounts may use it
        </label>
      </div>
      {!allAccounts ? (
        <div className="mb-5" style={{ maxWidth: 520 }}>
          {error ? <div className="alert alert-danger">{error}</div> : null}
          {accounts === null && !error ? <p className="text-muted">Loading the accounts...</p> : null}
          {accounts !== null ? (
            <>
              <input
                type="search"
                className="form-control form-control-sm mb-3"
                placeholder="Filter accounts"
                aria-label="Filter accounts"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
              />
              <div className="border rounded p-3" style={{ maxHeight: 280, overflowY: "auto" }}>
                {shown.map((account) => (
                  <div className="form-check mb-2" key={account.id}>
                    <input
                      id={`account-${account.id}`}
                      className="form-check-input"
                      type="checkbox"
                      checked={selected.has(account.id)}
                      onChange={() => toggle(account.id)}
                    />
                    <label className="form-check-label" htmlFor={`account-${account.id}`}>
                      {account.accountNumber} {account.companyName ? `· ${account.companyName}` : ""}
                    </label>
                  </div>
                ))}
              </div>
              <div className="form-text">{selected.size} selected.</div>
            </>
          ) : null}
        </div>
      ) : null}
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? <Spinner label="Saving" /> : null}
        Save availability
      </button>
    </form>
  );
}

/** The installed versions, and rolling back to one. */
function Versions({
  extension,
  busy,
  onRollback,
}: {
  extension: ExtensionDetail;
  busy: string | null;
  onRollback: (versionId: number, version: string) => void;
}) {
  return (
    <div className="table-responsive">
      <table className="table table-row-dashed align-middle gs-0 gy-3">
        <thead className="table-light">
          <tr className="fw-bold text-muted">
            <th>Version</th>
            <th>Installed</th>
            <th className="d-none d-md-table-cell">By</th>
            <th className="d-none d-lg-table-cell">sha256</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {extension.versions.map((version) => (
            <tr key={version.id}>
              <td>
                {version.version}
                {version.isInstalled ? <span className="badge badge-light-success ms-2">Running</span> : null}
              </td>
              <td>{version.createdAt ? formatDateTime(version.createdAt, "date") : ""}</td>
              <td className="d-none d-md-table-cell">{version.installedBy ?? ""}</td>
              <td className="d-none d-lg-table-cell">
                <code title={version.sha256}>{version.sha256.slice(0, 12)}</code>
              </td>
              <td className="text-end">
                {!version.isInstalled ? (
                  <button
                    type="button"
                    className="btn btn-sm btn-light"
                    disabled={busy !== null}
                    onClick={() => onRollback(version.id, version.version)}
                  >
                    {busy === `rollback:${version.id}` ? <Spinner label="Rolling back" /> : null}
                    Roll back to {version.version}
                  </button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The waffle switches that the extension owns, and the SAM resources that it created. */
function Resources({ extension }: { extension: ExtensionDetail }) {
  return (
    <>
      <h2 className="fs-5 fw-bold mb-3">Waffle switches</h2>
      {extension.switches.length === 0 ? (
        <p className="text-muted mb-8">This extension has no waffle switches.</p>
      ) : (
        <ul className="mb-8">
          {extension.switches.map((item) => (
            <li key={item.name}>
              <code>{item.name}</code> <span className="text-muted">{item.description}</span>{" "}
              <span className={`badge ${item.active ? "badge-light-success" : "badge-light"}`}>
                {item.active ? "On" : "Off"}
              </span>
            </li>
          ))}
        </ul>
      )}
      <h2 className="fs-5 fw-bold mb-3">Resources it created</h2>
      {extension.resources.length === 0 ? (
        <p className="text-muted">This extension has created no resources.</p>
      ) : (
        <ul>
          {extension.resources.map((resource) => (
            <li key={`${resource.kind}:${resource.name}`}>
              {resource.kind} <code>{resource.name}</code>{" "}
              <span className="text-muted">
                owned by {resource.owner}, from version {resource.version}
                {resource.managed ? "" : ", by a lifecycle hook"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
