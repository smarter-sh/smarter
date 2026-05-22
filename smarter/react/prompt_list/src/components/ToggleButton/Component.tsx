
/**
 * ToggleButton React Component
 *
 * This component provides a UI control for toggling between two view modes: "list" and "thumbnail".
 * It displays two buttons, each representing a view mode, and highlights the active mode.
 *
 * Features:
 * - Allows users to switch between list and thumbnail views.
 * - Visually indicates the currently selected view mode.
 * - Accessible with appropriate ARIA labels and button roles.
 *
 * Props:
 * - viewMode ("list" | "thumbnail"): The currently selected view mode.
 * - setViewMode ((mode: ViewMode) => void): Callback to update the view mode when a button is clicked.
 *
 * Usage:
 * <ToggleButton viewMode={viewMode} setViewMode={setViewMode} />
 *
 * The component expects the parent to manage the viewMode state and provide a setter function.
 */
export type ViewMode = "list" | "thumbnail";


interface ViewToggleButtonProps {
  viewMode: ViewMode;
  onClick: () => void;
}

function ListViewToggleButton({ viewMode, onClick }: ViewToggleButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn-sm ${viewMode === "list" ? "btn-primary" : "btn-outline-secondary"}`}
      title="List View"
      aria-label="List View"
      onClick={onClick}
    >
      <i className="fas fa-list" />
    </button>
  );
}

function ThumbnailViewToggleButton({
  viewMode,
  onClick,
}: ViewToggleButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn-sm ${viewMode === "thumbnail" ? "btn-primary" : "btn-outline-secondary"}`}
      title="Thumbnail View"
      aria-label="Thumbnail View"
      onClick={onClick}
    >
      <i className="fas fa-th-large" />
    </button>
  );
}

export default function ToggleButton({
  viewMode,
  setViewMode,
}: {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}) {
  return (
    <div id="toggle-buttons" className="p-3">
      <div
        className="btn-group border border-light rounded-3 bg-white"
        role="group"
        aria-label="View toggle"
      >
        <ListViewToggleButton
          viewMode={viewMode}
          onClick={() => setViewMode("list")}
        />
        <ThumbnailViewToggleButton
          viewMode={viewMode}
          onClick={() => setViewMode("thumbnail")}
        />
      </div>
    </div>
  );
}
