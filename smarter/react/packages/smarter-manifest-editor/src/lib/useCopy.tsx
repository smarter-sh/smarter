import { useState } from "react";
import type * as monaco from "monaco-editor";

import { loggerPrefix } from "@/const";

/** Copy the editor's YAML to the clipboard, and briefly show that it was copied. */
export function useCopy(editor: monaco.editor.IStandaloneCodeEditor | null) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    const value = editor?.getValue();
    if (!value) return;
    await navigator.clipboard.writeText(value);
    console.debug(loggerPrefix, "Copied the manifest to the clipboard");
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  };
  return { copied, copy };
}
