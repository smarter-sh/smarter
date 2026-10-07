/** The response of the Smarter API to an applied manifest: the parts that the modal shows. */
export type ApplyResult = {
  message?: string | null;
  data?: {
    data?: {
      metadata?: { name?: string; version?: string; description?: string };
    };
  };
};

type ModalState = {
  open: boolean;
  title: string;
  /** The apply result, or an error message. */
  data?: ApplyResult | string | null;
  isError?: boolean;
};

export type DropZoneModalProps = ModalState & {
  onClose: () => void;
};

export default function DropZoneModal({ open, title, data, isError = false, onClose }: DropZoneModalProps) {
  if (!open) return null;

  const color = isError ? "#dc3545" : "#28a745";

  console.debug("DropZoneModal data:", data);

  const result = typeof data === "string" ? null : data;
  const response = {
    name: result?.data?.data?.metadata?.name ?? "Unknown",
    version: result?.data?.data?.metadata?.version ?? "Unknown",
    description: result?.data?.data?.metadata?.description ?? "No description provided",
    message: result?.message ?? null,
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.4)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        zIndex: 9999,
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dropzone-modal-title"
        style={{
          background: "#fff",
          padding: 20,
          borderRadius: 8,
          maxWidth: 520,
          width: "90%",
          position: "relative",
        }}
      >
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          style={{
            position: "absolute",
            top: 8,
            right: 12,
            fontSize: 18,
            background: "none",
            border: "none",
            cursor: "pointer",
          }}
        >
          ×
        </button>

        <div id="dropzone-modal-title" style={{ fontWeight: 600, fontSize: 18, marginBottom: 8 }}>
          {title}
        </div>

        {response.message && <div style={{ color, marginBottom: 16 }}>{response.message}</div>}

        {/* SUCCESS VIEW (clean summary) */}
        {!isError && data && (
          <div
            style={{
              background: "#f6f8fa",
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              padding: 12,
              fontSize: 13,
            }}
          >
            <div>
              <strong>Name:</strong> {response.name}
            </div>
            <div>
              <strong>Version:</strong> {response.version}
            </div>
            <div>
              <strong>Description:</strong> {response.description}
            </div>
          </div>
        )}

        {/* ERROR VIEW (debug only) */}
        {isError && data && (
          <pre
            style={{
              maxHeight: 220,
              overflow: "auto",
              background: "#fff5f5",
              border: "1px solid #ffd6d6",
              padding: 10,
              borderRadius: 4,
              fontSize: 12,
            }}
          >
            {JSON.stringify(data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
