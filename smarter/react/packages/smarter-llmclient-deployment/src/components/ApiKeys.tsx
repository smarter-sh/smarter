/**
 * The LLMClient's api key, managed in place, in the workbench's "Deployment" tab: its attached key, the
 * account's api keys that the user may manage, with a button that attaches each, and a form that
 * creates one. A new key's secret is shown once, right after it is created.
 */
import { useState, type FormEvent } from "react";
import { formatDateTime, gettext, interpolateNodes, type SessionContext } from "@smarter/common";

import Terminal from "./Terminal";
import { attachApiKey, createApiKey, detachApiKey } from "../lib/api";
import { errorMessage, successMessage, type ApiKeyAction } from "../lib/messages";
import type { ApiKeyActionResponse, DeploymentApiKeys, LLMClientDeploymentPage, NewApiKey } from "../lib/types";

/** What the last action did, or why it failed. */
type Notice = { level: "success" | "danger"; text: string };

interface ApiKeysProps {
  apiKeys: DeploymentApiKeys;
  /** The command that a platform administrator runs to create an api key, for a user who may not. */
  createApiKeyCommand: string;
  /** The web console's API Keys page. */
  apiKeysUrl: string;
  session: SessionContext;
  /** Called with the page as it is after an action. */
  onPage: (page: LLMClientDeploymentPage) => void;
}

/** Whether the attached api key requires every request to the url, and the Detach button. */
function AttachedKey({ apiKeys, busy, onDetach }: { apiKeys: DeploymentApiKeys; busy: boolean; onDetach: () => void }) {
  const { attached } = apiKeys;
  let status;
  if (!attached) {
    status = (
      <>
        <i className="ki-outline ki-lock-2 fs-3 text-warning me-2" aria-hidden="true" />
        {gettext("No api key is attached: the url is public.")}
      </>
    );
  } else if (attached.isActive) {
    status = (
      <>
        <i className="ki-outline ki-lock fs-3 text-success me-2" aria-hidden="true" />
        {interpolateNodes(gettext("Every request to the url needs %(name)s."), {
          name: <strong>{attached.name}</strong>,
        })}
      </>
    );
  } else {
    status = (
      <>
        <i className="ki-outline ki-shield-cross fs-3 text-warning me-2" aria-hidden="true" />
        {interpolateNodes(
          gettext(
            "%(name)s is attached, but turned off, so the url is public. Turn it on in API Keys, or attach another key.",
          ),
          { name: <strong>{attached.name}</strong> },
        )}
      </>
    );
  }
  return (
    <div className="d-flex flex-wrap align-items-center justify-content-between gap-4 bg-light rounded p-5 mb-8">
      <div className="fs-6 text-gray-700">{status}</div>
      {attached && apiKeys.canManage && (
        <button type="button" className="btn btn-sm btn-light-danger fw-bold" disabled={busy} onClick={onDetach}>
          {gettext("Detach")}
        </button>
      )}
    </div>
  );
}

/** The form that creates an api key, and attaches it if the user may and wants to. */
function CreateForm({
  canAttach,
  busy,
  onCreate,
}: {
  canAttach: boolean;
  busy: boolean;
  onCreate: (name: string, description: string, attach: boolean) => Promise<boolean>;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [attach, setAttach] = useState(true);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (await onCreate(name, description, canAttach && attach)) {
      setName("");
      setDescription("");
    }
  };
  return (
    <form className="mb-6" onSubmit={submit}>
      <div className="row g-4 mb-4">
        <div className="col-md-5">
          <label htmlFor="smarter-api-key-name" className="form-label fw-semibold">
            {gettext("Name")}
          </label>
          <input
            id="smarter-api-key-name"
            type="text"
            required
            maxLength={255}
            pattern="[a-z0-9_]+"
            className="form-control form-control-solid"
            placeholder="my_site_chat"
            autoComplete="off"
            aria-describedby="smarter-api-key-name-help"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <div id="smarter-api-key-name-help" className="form-text">
            {gettext("snake_case: the name that the manifest's spec.apiKey uses.")}
          </div>
        </div>
        <div className="col-md-7">
          <label htmlFor="smarter-api-key-description" className="form-label fw-semibold">
            {gettext("Description")}
          </label>
          <input
            id="smarter-api-key-description"
            type="text"
            maxLength={255}
            className="form-control form-control-solid"
            placeholder={gettext("The chat on www.example.com")}
            autoComplete="off"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>
      </div>
      {canAttach && (
        <div className="form-check form-check-custom form-check-solid mb-5">
          <input
            id="smarter-api-key-attach"
            type="checkbox"
            className="form-check-input"
            checked={attach}
            onChange={(event) => setAttach(event.target.checked)}
          />
          <label htmlFor="smarter-api-key-attach" className="form-check-label text-gray-700">
            {gettext("Attach it to this LLMClient")}
          </label>
        </div>
      )}
      <button type="submit" className="btn btn-primary fw-bold" disabled={busy}>
        <i className="ki-outline ki-key fs-3" aria-hidden="true" />
        {gettext("Create the api key")}
      </button>
    </form>
  );
}

export default function ApiKeys({ apiKeys, createApiKeyCommand, apiKeysUrl, session, onPage }: ApiKeysProps) {
  const [notice, setNotice] = useState<Notice | null>(null);
  const [newApiKey, setNewApiKey] = useState<NewApiKey | null>(null);
  const [busy, setBusy] = useState(false);

  /** Run an action, then show the page as it now is, and what the action did. */
  const run = async (
    request: () => Promise<ApiKeyActionResponse>,
    done: (response: ApiKeyActionResponse) => ApiKeyAction,
    name = "",
  ): Promise<boolean> => {
    setBusy(true);
    try {
      const response = await request();
      onPage(response.page);
      setNewApiKey(response.newApiKey);
      setNotice({ level: "success", text: successMessage(done(response)) });
      return true;
    } catch (error) {
      setNewApiKey(null);
      setNotice({ level: "danger", text: errorMessage(error, name) });
      return false;
    } finally {
      setBusy(false);
    }
  };

  const create = (name: string, description: string, attach: boolean) =>
    run(
      () => createApiKey(session, apiKeys, { name, description, attach }),
      (response) => ({
        action: "create",
        name: response.newApiKey?.name ?? name,
        attached: response.page.apiKeys?.attached?.name === response.newApiKey?.name,
      }),
      name,
    );
  const attach = (keyId: string, name: string) =>
    run(
      () => attachApiKey(session, apiKeys, { keyId }),
      () => ({ action: "attach", name }),
    );
  const detach = () =>
    run(
      () => detachApiKey(session, apiKeys),
      () => ({ action: "detach" }),
    );

  return (
    <div className="card card-flush shadow-sm h-100">
      <div className="card-body p-8">
        <div className="d-flex align-items-center mb-6">
          <span className="smarter-step me-3">1</span>
          <h3 className="fw-bold text-gray-900 mb-0">{gettext("Choose its api key")}</h3>
        </div>

        {notice && (
          <div className={`alert alert-${notice.level} d-flex align-items-center p-5 mb-6`} role="status">
            <i
              className={`ki-outline ${notice.level === "success" ? "ki-check-circle" : "ki-information"} fs-2 me-3`}
              aria-hidden="true"
            />
            <div className="fs-6">{notice.text}</div>
          </div>
        )}

        {newApiKey && (
          <div className="notice bg-light-warning rounded border-warning border border-dashed p-6 mb-6">
            <h4 className="text-gray-900 fw-bold mb-2">{gettext("Copy its secret now")}</h4>
            <p className="fs-6 text-gray-700 mb-4">
              {interpolateNodes(
                gettext(
                  "This is the secret of %(name)s. Smarter keeps only a hash of it, and can't show it again: store it somewhere safe, such as a password manager or your hosting's secrets. It is what your front end sends, in place of %(placeholder)s.",
                ),
                { name: newApiKey.name, placeholder: <code>{"<YOUR-API-KEY>"}</code> },
              )}
            </p>
            <Terminal title={newApiKey.name} code={newApiKey.secret} />
          </div>
        )}

        <AttachedKey apiKeys={apiKeys} busy={busy} onDetach={detach} />

        <h4 className="fw-bold text-gray-900 mb-4">{gettext("Your account's api keys")}</h4>
        {apiKeys.apiKeys.length ? (
          <div className="table-responsive mb-8">
            <table className="table table-row-dashed align-middle fs-6 gy-3 mb-0">
              <thead>
                <tr className="text-gray-500 fw-bold fs-7 text-uppercase">
                  <th>{gettext("Name")}</th>
                  <th className="d-none d-md-table-cell">{gettext("Owner")}</th>
                  <th>{gettext("Status")}</th>
                  <th className="d-none d-md-table-cell">{gettext("Last used")}</th>
                  <th className="text-end">
                    <span className="visually-hidden">{gettext("Actions")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {apiKeys.apiKeys.map((apiKey) => (
                  <tr key={apiKey.keyId}>
                    <td>
                      <div className="fw-semibold text-gray-900">{apiKey.name}</div>
                      {apiKey.description && <div className="text-gray-500 fs-7">{apiKey.description}</div>}
                    </td>
                    <td className="d-none d-md-table-cell text-gray-700">{apiKey.owner}</td>
                    <td>
                      {apiKey.isActive ? (
                        <span className="badge badge-light-success">{gettext("On")}</span>
                      ) : (
                        <span className="badge badge-light">{gettext("Off")}</span>
                      )}
                    </td>
                    <td className="d-none d-md-table-cell text-gray-600">
                      {apiKey.lastUsedAt ? formatDateTime(apiKey.lastUsedAt) : gettext("Never")}
                    </td>
                    <td className="text-end">
                      {apiKey.isAttached ? (
                        <span className="badge badge-light-primary fs-7">{gettext("Attached")}</span>
                      ) : (
                        apiKeys.canManage && (
                          <button
                            type="button"
                            className="btn btn-sm btn-light-primary fw-bold"
                            disabled={busy}
                            onClick={() => attach(apiKey.keyId, apiKey.name)}
                          >
                            {gettext("Attach")}
                          </button>
                        )
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-600 fs-6 mb-8">{gettext("There are no api keys that you can manage yet.")}</p>
        )}
        {!apiKeys.canManage && (
          <p className="text-gray-600 fs-6 mb-8">
            {gettext("Only the LLMClient's owner, or an account admin, can change its api key.")}
          </p>
        )}

        <h4 className="fw-bold text-gray-900 mb-4">{gettext("Create an api key")}</h4>
        {apiKeys.canCreate ? (
          <>
            <CreateForm canAttach={apiKeys.canManage} busy={busy} onCreate={create} />
            <p className="text-gray-600 fs-7 mb-0">
              {gettext(
                "The key is yours. Its secret is shown once, right after you create it. The web console's API Keys page lists your keys, and turns a key off without deleting it.",
              )}{" "}
              <a href={apiKeysUrl} target="_top" className="fw-semibold">
                {gettext("API Keys")}
              </a>
            </p>
          </>
        ) : (
          <>
            <p className="text-gray-600 fs-6 mb-4">
              {gettext(
                "Only an account admin can create api keys. Ask one to create a key for you, then attach it here, or ask them to run:",
              )}
            </p>
            <Terminal title="bash" code={createApiKeyCommand} />
          </>
        )}
      </div>
    </div>
  );
}
