

type ModalState = {
  open: boolean;
  title: string;
  data?: any;
  isError?: boolean;
};

export type DropZoneModalProps = ModalState & {
  onClose: () => void;
};

export default function DropZoneModal({
  open,
  title,
  data,
  isError = false,
  onClose,
}: DropZoneModalProps) {
  if (!open) return null;

  const color = isError ? "#dc3545" : "#28a745";

  console.debug("DropZoneModal data:", data);

  const response = {
    name: data?.data?.data?.metadata.name ?? "Unknown",
    version: data?.data?.data?.metadata.version ?? "Unknown",
    description: data?.data?.data?.metadata.description ?? "No description provided",
    message: data?.message ?? null,
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

        <div style={{ fontWeight: 600, fontSize: 18, marginBottom: 8 }}>
          {title}
        </div>

        {response.message && (
          <div style={{ color, marginBottom: 16 }}>
            {response.message}
          </div>
        )}

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
            <div><strong>Name:</strong> {response.name}</div>
            <div><strong>Version:</strong> {response.version}</div>
            <div><strong>Description:</strong> {response.description}</div>
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
