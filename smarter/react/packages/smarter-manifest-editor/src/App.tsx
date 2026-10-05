/**
 * Manifest Editor
 *
 * Views and edits a Smarter manifest, and saves, clones and deletes its resource with the
 * cli api. It replaces the read-only manifest of templates/common/manifest_detail.html.
 *
 * As the user edits it, it checks the manifest's YAML syntax, and then validates it against its
 * SAM model with the cli api's validate command, and marks the errors in the editor.
 */
import { useEffect, useMemo, useState } from "react";
import { load } from "js-yaml";
import type * as monaco from "monaco-editor";

import { Modal } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import ManifestEditor from "@/components/ManifestEditor";
import Problems from "@/components/Problems";
import Toolbar from "@/components/Toolbar";
import { callCli, type CliResult } from "@/lib/api";
import { cloneManifest, manifestDependencies, manifestToApply, parseManifest, type Manifest } from "@/lib/manifest";
import { samErrors, syntaxErrors, type ManifestError } from "@/lib/validation";

// how long the user pauses typing before the manifest is validated.
const VALIDATE_DELAY_MS = 600;

export interface AppProps {
  sessionContext: SessionContext;
  initialManifest: string;
  applyApiUrl: string;
  validateApiUrl: string;
  deleteApiUrl: string;
  kindPlaceholder: string;
}

type ModalState =
  | { type: null }
  | { type: "clone" }
  | { type: "delete" }
  | { type: "result"; title: string; result: CliResult; afterClose?: () => void };

/** Parse a manifest, or return null if it is not valid. */
function tryParse(yaml: string): Manifest | null {
  try {
    return parseManifest(yaml);
  } catch {
    return null;
  }
}

/** Leave the page after its resource is deleted: back to where the user came from, or the dashboard. */
function leavePage() {
  const referrer = document.referrer ? new URL(document.referrer) : null;
  if (referrer && referrer.origin === window.location.origin && referrer.pathname !== window.location.pathname) {
    window.location.assign(referrer.href);
  } else {
    window.location.assign("/dashboard/");
  }
}

interface CloneModalProps {
  kind: string;
  name: string;
  onOk: (newName: string) => void;
  onCancel: () => void;
}

function CloneModal({ kind, name, onOk, onCancel }: CloneModalProps) {
  const [newName, setNewName] = useState("");
  return (
    <Modal show title={`Clone ${kind}`} onOk={() => onOk(newName.trim())} onCancel={onCancel}>
      <p>
        Clone {kind} <strong>{name}</strong> to a new resource owned by you.
      </p>
      <p>
        <em>Provide the new name for the cloned {kind}.</em>
      </p>
      <input
        className="form-control"
        value={newName}
        onChange={(e) => setNewName(e.target.value)}
        placeholder={`Enter new ${kind} name`}
        aria-label={`New ${kind} name`}
        // focus moves into the dialog that just opened, as dialogs should do.
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus
      />
    </Modal>
  );
}

function App({
  sessionContext,
  initialManifest,
  applyApiUrl,
  validateApiUrl,
  deleteApiUrl,
  kindPlaceholder,
}: AppProps) {
  const [editor, setEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [savedYaml, setSavedYaml] = useState(initialManifest);
  const [yaml, setYaml] = useState(initialManifest);
  const [isBusy, setIsBusy] = useState(false);
  const [modal, setModal] = useState<ModalState>({ type: null });
  const [errors, setErrors] = useState<ManifestError[]>([]);
  const [isValidating, setIsValidating] = useState(true);

  // when the user pauses typing: check the YAML's syntax, then validate it against its SAM model.
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(async () => {
      setIsValidating(true);
      const syntax = syntaxErrors(yaml);
      if (syntax.length) {
        setErrors(syntax);
        setIsValidating(false);
        return;
      }
      const parsed = load(yaml);
      const manifest = parsed && typeof parsed === "object" ? manifestToApply(parsed as Manifest) : parsed;
      try {
        const found = await samErrors(sessionContext, validateApiUrl, yaml, manifest);
        if (!cancelled) setErrors(found);
      } catch (error) {
        console.warn("Manifest validation failed:", error);
        if (!cancelled) setErrors([]);
      } finally {
        if (!cancelled) setIsValidating(false);
      }
    }, VALIDATE_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [yaml, sessionContext, validateApiUrl]);

  // the saved resource's manifest, which identifies the resource to clone and delete.
  const saved = useMemo(() => tryParse(savedYaml), [savedYaml]);
  const kind = saved?.kind ?? "resource";
  const name = saved?.metadata.name ?? "";
  const dependencies = manifestDependencies(saved);
  const isDirty = yaml !== savedYaml;

  const deleteTitle = dependencies.length
    ? `Delete: You can't delete this ${kind}, because these resources depend on it: ${dependencies
        .map((d) => `${d.kind} ${d.name}`)
        .join(", ")}`
    : `Delete: Delete this ${kind}`;

  const showResult = (title: string, result: CliResult, afterClose?: () => void) =>
    setModal({ type: "result", title, result, afterClose });

  /** Run a cli api call, and return its result, or the error that it raised. */
  const run = async (call: () => Promise<CliResult>): Promise<CliResult> => {
    setIsBusy(true);
    try {
      return await call();
    } catch (error) {
      return { ok: false, message: error instanceof Error ? error.message : String(error) };
    } finally {
      setIsBusy(false);
    }
  };

  const handleSave = async () => {
    let manifest: Manifest;
    try {
      manifest = parseManifest(yaml);
    } catch (error) {
      showResult("Save Failed", { ok: false, message: error instanceof Error ? error.message : String(error) });
      return;
    }
    const result = await run(() =>
      callCli(
        sessionContext,
        applyApiUrl,
        manifestToApply(manifest),
        `${manifest.kind} ${manifest.metadata.name} saved`,
      ),
    );
    if (result.ok) setSavedYaml(yaml);
    showResult(result.ok ? "Saved" : "Save Failed", result);
  };

  const handleRevert = () => {
    editor?.setValue(savedYaml);
    setYaml(savedYaml);
  };

  const handleClone = async (newName: string) => {
    setModal({ type: null });
    if (!saved || !newName) return;
    const result = await run(() =>
      callCli(sessionContext, applyApiUrl, cloneManifest(saved, newName), `${kind} ${newName} created`),
    );
    showResult(result.ok ? "Cloned" : "Clone Failed", result);
  };

  const handleDelete = async () => {
    setModal({ type: null });
    if (!saved) return;
    const url = `${deleteApiUrl.replace(kindPlaceholder, encodeURIComponent(kind))}?name=${encodeURIComponent(name)}`;
    const result = await run(() => callCli(sessionContext, url, {}, `${kind} ${name} deleted`));
    showResult(result.ok ? "Deleted" : "Delete Failed", result, result.ok ? leavePage : undefined);
  };

  const closeResult = () => {
    const afterClose = modal.type === "result" ? modal.afterClose : undefined;
    setModal({ type: null });
    afterClose?.();
  };

  return (
    <div className="card border shadow-sm manifest-editor">
      <div className="card-header min-h-auto py-3 px-4">
        <Toolbar
          editor={editor}
          isDirty={isDirty}
          problemCount={errors.length}
          isBusy={isBusy}
          fileName={`${name || "manifest"}.yaml`}
          canDelete={Boolean(saved) && dependencies.length === 0}
          deleteTitle={deleteTitle}
          onSave={handleSave}
          onRevert={handleRevert}
          onClone={() => setModal({ type: "clone" })}
          onDelete={() => setModal({ type: "delete" })}
        />
      </div>
      <div className="card-body p-0">
        <ManifestEditor value={yaml} errors={errors} editor={editor} onEditorDidMount={setEditor} onChange={setYaml} />
      </div>
      <div className="card-footer py-3 px-4">
        <Problems errors={errors} isValidating={isValidating} editor={editor} />
      </div>

      {modal.type === "clone" && (
        <CloneModal kind={kind} name={name} onOk={handleClone} onCancel={() => setModal({ type: null })} />
      )}
      {modal.type === "delete" && (
        <Modal show title={`Delete ${kind}`} onOk={handleDelete} onCancel={() => setModal({ type: null })}>
          <p>
            Are you sure you want to delete {kind} <strong>{name}</strong>?
          </p>
          {isDirty && (
            <p>
              <em>Your unsaved changes will be lost.</em>
            </p>
          )}
        </Modal>
      )}
      {modal.type === "result" && (
        <Modal show title={modal.title} onClose={closeResult}>
          <p className={modal.result.ok ? "" : "text-danger"}>{modal.result.message}</p>
        </Modal>
      )}
    </div>
  );
}

export default App;
