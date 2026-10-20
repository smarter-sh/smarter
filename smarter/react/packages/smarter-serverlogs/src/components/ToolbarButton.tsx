/**
 * A button of the server log viewer's toolbar: an icon, and optionally its label, in the palette of
 * the web console's terminal. The viewer's toolbar uses it, and so do the toolbars of other dark
 * viewers that want the same look, e.g. the Prompt Passthrough's Request and Response editors.
 *
 * A button with aria-pressed is a toggle, e.g. wrap: it is highlighted while it is on.
 */
import type { ReactNode } from "react";

import "../styles.css";

/** The toolbar's icons, by name. */
export type ToolbarIcon = "wrap" | "expandJson" | "follow" | "copy" | "fullscreen" | "help";

const ICON_PATHS: Record<ToolbarIcon, string> = {
  wrap: "M1 3.5a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 0 1h-13a.5.5 0 0 1-.5-.5Zm0 4a.5.5 0 0 1 .5-.5h11a2.5 2.5 0 0 1 0 5H9.707l.647.646a.5.5 0 0 1-.708.708l-1.5-1.5a.5.5 0 0 1 0-.708l1.5-1.5a.5.5 0 1 1 .708.708L9.707 11H12.5a1.5 1.5 0 0 0 0-3h-11a.5.5 0 0 1-.5-.5Zm0 4a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 0 1h-4a.5.5 0 0 1-.5-.5Z",
  expandJson:
    "M3.5 2a.5.5 0 0 0-.5.5v11a.5.5 0 0 0 .5.5H5a.5.5 0 0 0 0-1H4V3h1a.5.5 0 0 0 0-1H3.5Zm9 0H11a.5.5 0 0 0 0 1h1v10h-1a.5.5 0 0 0 0 1h1.5a.5.5 0 0 0 .5-.5v-11a.5.5 0 0 0-.5-.5ZM6 8a1 1 0 1 1 2 0 1 1 0 0 1-2 0Zm3 0a1 1 0 1 1 2 0 1 1 0 0 1-2 0Z",
  follow:
    "M8 1a.5.5 0 0 1 .5.5v9.793l3.146-3.147a.5.5 0 0 1 .708.708l-4 4a.5.5 0 0 1-.708 0l-4-4a.5.5 0 1 1 .708-.708L7.5 11.293V1.5A.5.5 0 0 1 8 1ZM2 14.5a.5.5 0 0 1 .5-.5h11a.5.5 0 0 1 0 1h-11a.5.5 0 0 1-.5-.5Z",
  copy: "M4 2a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V2Zm2-1a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H6ZM2 5a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1v-1h1v1a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h1v1H2Z",
  fullscreen:
    "M1.5 1h4a.5.5 0 0 1 0 1H2v3.5a.5.5 0 0 1-1 0v-4a.5.5 0 0 1 .5-.5Zm9 0h4a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-1 0V2h-3.5a.5.5 0 0 1 0-1ZM1.5 10a.5.5 0 0 1 .5.5V14h3.5a.5.5 0 0 1 0 1h-4a.5.5 0 0 1-.5-.5v-4a.5.5 0 0 1 .5-.5Zm13 0a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5h-4a.5.5 0 0 1 0-1H14v-3.5a.5.5 0 0 1 .5-.5Z",
  help: "M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14Zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16Zm-2.5-10.5a2.5 2.5 0 1 1 3.4 2.33c-.53.21-.9.6-.9 1.17v.5a.5.5 0 0 1-1 0V9c0-1.1.73-1.86 1.53-2.18A1.5 1.5 0 1 0 6.5 5.5a.5.5 0 0 1-1 0ZM8 12.25a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z",
};

export interface ToolbarButtonProps {
  icon: ToolbarIcon;
  /** The button's accessible name, and its text when showLabel is true. */
  label: string;
  title: string;
  /** Whether a toggle is on. Leave it undefined for a button that isn't a toggle. */
  pressed?: boolean;
  onClick: () => void;
  showLabel?: boolean;
}

function ToolbarButton({ icon, label, title, pressed, onClick, showLabel = false }: ToolbarButtonProps): ReactNode {
  return (
    <button
      type="button"
      className="console-server-logs-button"
      aria-pressed={pressed}
      aria-label={showLabel ? undefined : label}
      title={title}
      onClick={onClick}
    >
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" fill="currentColor">
        <path d={ICON_PATHS[icon]} />
      </svg>
      {showLabel && label}
    </button>
  );
}

export default ToolbarButton;
