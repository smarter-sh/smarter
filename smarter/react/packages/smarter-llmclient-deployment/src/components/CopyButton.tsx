/** A button that copies a text to the clipboard, and says "Copied" for a moment afterwards. */
import { useEffect, useRef, useState } from "react";
import { gettext } from "@smarter/common";

import { loggerPrefix } from "../lib/const";

/** How long the button says "Copied", in milliseconds. */
export const COPIED_MILLISECONDS = 1500;

export default function CopyButton({ text }: { text: string }) {
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
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error(loggerPrefix, "Could not copy to the clipboard:", error);
      return;
    }
    setCopied(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), COPIED_MILLISECONDS);
  };

  return (
    <button type="button" className="smarter-terminal-copy" onClick={copy}>
      {copied ? gettext("Copied") : gettext("Copy")}
    </button>
  );
}
