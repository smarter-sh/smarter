/**
 * A manifest excerpt to paste into the LLMClient's manifest: the lines that it goes beneath, dimmed, then the lines
 * to add. The Copy button copies only the lines to add, and says "Copied" for a moment afterwards.
 */
import { useEffect, useRef, useState } from "react";
import { gettext } from "@smarter/common";

import { loggerPrefix } from "../lib/const";
import type { ManifestSnippet as Snippet } from "../lib/gettingStarted";

/** How long the button says "Copied", in milliseconds. */
export const COPIED_MILLISECONDS = 1500;

interface ManifestSnippetProps {
  snippet: Snippet;
  /** The excerpt's name, for screen readers, e.g. "A Guardrail, in the manifest". */
  label: string;
}

export default function ManifestSnippet({ snippet, label }: ManifestSnippetProps) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${snippet.code}\n`);
    } catch (error) {
      console.error(loggerPrefix, "Could not copy to the clipboard:", error);
      return;
    }
    setCopied(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), COPIED_MILLISECONDS);
  };

  return (
    <div className="architecture-snippet" role="group" aria-label={label}>
      <div className="architecture-snippet-bar">
        <span className="architecture-snippet-title">manifest.yaml</span>
        <button type="button" className="architecture-snippet-copy" onClick={copy}>
          <i className={`ki-outline ki-${copied ? "check" : "copy"} fs-7 me-1`} aria-hidden="true" />
          {copied ? gettext("Copied") : gettext("Copy")}
        </button>
      </div>
      <pre className="architecture-snippet-code">
        <code>
          <span className="architecture-snippet-context" aria-hidden="true">
            {`${snippet.context}\n`}
          </span>
          <span className="architecture-snippet-added">{snippet.code}</span>
        </code>
      </pre>
    </div>
  );
}
