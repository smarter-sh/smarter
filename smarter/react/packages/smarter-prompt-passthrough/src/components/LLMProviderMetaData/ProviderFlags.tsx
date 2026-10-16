import type { LLMProvider } from "@/components/LLMProviders";
import { gettext } from "@smarter/common";

interface ProviderFlagsProps {
  provider: LLMProvider;
}

export default function ProviderFlags({ provider }: ProviderFlagsProps) {
  const flags = [
    { label: gettext("Active"), enabled: provider.isActive },
    { label: gettext("Default"), enabled: provider.isDefault },
    { label: gettext("Verified"), enabled: provider.isVerified },
    { label: gettext("Featured"), enabled: provider.isFeatured },
    { label: gettext("Official"), enabled: provider.isOfficialProvider },
    { label: gettext("Deprecated"), enabled: provider.isDeprecated },
    { label: gettext("Flagged"), enabled: provider.isFlagged },
    { label: gettext("Suspended"), enabled: provider.isSuspended },
  ];

  return (
    <div className="mt-2">
      <strong>{gettext("Flags:")}</strong>{" "}
      {flags.map((flag) => (
        <span key={flag.label} className={`badge me-1 ${flag.enabled ? "text-bg-success" : "text-bg-light border"}`}>
          {flag.label}
        </span>
      ))}
    </div>
  );
}
