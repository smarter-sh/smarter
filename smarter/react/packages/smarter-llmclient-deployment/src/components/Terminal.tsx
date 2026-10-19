/**
 * A terminal window, whose Copy button copies its text: a title bar, and a console. Every command,
 * manifest excerpt and code snippet on the page is in one.
 */
import type { ReactNode } from "react";

import CopyButton from "./CopyButton";

interface TerminalProps {
  /** The title bar's text, e.g. bash, manifest.yaml or Chat.tsx. */
  title: string;
  /** The text that the Copy button copies. */
  code: string;
  /** What the console shows, if it isn't the text itself, e.g. highlighted YAML. */
  children?: ReactNode;
  /** Limit the console's height, and scroll it. */
  tall?: boolean;
}

export default function Terminal({ title, code, children, tall = false }: TerminalProps) {
  return (
    <div className="smarter-terminal" role="group" aria-label={title}>
      <div className="smarter-terminal-bar">
        <span className="smarter-terminal-dot smarter-terminal-dot-close" />
        <span className="smarter-terminal-dot smarter-terminal-dot-minimize" />
        <span className="smarter-terminal-dot smarter-terminal-dot-zoom" />
        <span className="smarter-terminal-title">{title}</span>
        <CopyButton text={code} />
      </div>
      <pre className={`smarter-console${tall ? " smarter-console-tall" : ""}`}>
        <code>{children ?? code}</code>
      </pre>
    </div>
  );
}
