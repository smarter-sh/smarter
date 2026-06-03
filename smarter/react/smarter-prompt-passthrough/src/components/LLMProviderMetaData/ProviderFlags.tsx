import type { LLMProvider } from "../LLMProviders";

interface ProviderFlagsProps {
  provider: LLMProvider;
}

export default function ProviderFlags({ provider }: ProviderFlagsProps) {
  const flags = [
    { label: "Active", enabled: provider.isActive },
    { label: "Default", enabled: provider.isDefault },
    { label: "Verified", enabled: provider.isVerified },
    { label: "Featured", enabled: provider.isFeatured },
    { label: "Official", enabled: provider.isOfficialProvider },
    { label: "Deprecated", enabled: provider.isDeprecated },
    { label: "Flagged", enabled: provider.isFlagged },
    { label: "Suspended", enabled: provider.isSuspended },
  ];

  return (
    <div className="mt-2">
      <strong>Flags:</strong>{" "}
      {flags.map((flag) => (
        <span
          key={flag.label}
          className={`badge me-1 ${flag.enabled ? "text-bg-success" : "text-bg-light border"}`}
        >
          {flag.label}
        </span>
      ))}
    </div>
  );
}
