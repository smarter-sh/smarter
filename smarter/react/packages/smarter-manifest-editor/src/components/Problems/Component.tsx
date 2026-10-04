/**
 * Problems Component
 *
 * The manifest's errors, as a compact list in the editor card's footer, like the Problems
 * panel of VS Code. Clicking an error moves the editor's cursor to it.
 */
import type * as monaco from "monaco-editor";

import type { ManifestError } from "@/lib/validation";

import "./styles.css";

interface ProblemsProps {
  errors: ManifestError[];
  isValidating: boolean;
  editor: monaco.editor.IStandaloneCodeEditor | null;
}

/** The label of an error's path, e.g. spec.config.stage, or nothing for a syntax error. */
function locLabel(error: ManifestError): string {
  return error.loc.length ? `${error.loc.join(".")}: ` : "";
}

function Problems({ errors, isValidating, editor }: ProblemsProps) {
  const model = editor?.getModel();

  const reveal = (error: ManifestError) => {
    if (!editor || !model) return;
    const position = model.getPositionAt(error.offset);
    editor.revealLineInCenter(position.lineNumber);
    editor.setPosition(position);
    editor.focus();
  };

  if (!errors.length) {
    return (
      <div className="manifest-editor-problems text-muted">
        {isValidating ? (
          <span>Checking the manifest…</span>
        ) : (
          <span>
            <i className="bi bi-check-circle text-success me-2" />
            No problems
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="manifest-editor-problems">
      <div className="fw-semibold mb-1">
        <i className="bi bi-x-circle text-danger me-2" />
        {errors.length} {errors.length === 1 ? "problem" : "problems"}
      </div>
      <ul className="list-unstyled mb-0">
        {errors.map((error, index) => {
          const line = model ? model.getPositionAt(error.offset).lineNumber : null;
          return (
            <li key={`${error.offset}-${index}`}>
              <button type="button" className="btn btn-link btn-sm p-0 text-start" onClick={() => reveal(error)}>
                {line !== null && <span className="text-muted me-2">Line {line}</span>}
                {locLabel(error)}
                {error.message}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default Problems;
