import type { LLMProvider } from "../LLMProviders";

interface ProviderMetaDataProps {
  provider: LLMProvider | null;
}

export default function LLMProviderMetaData({ provider }: ProviderMetaDataProps) {
  if (!provider) {
    return null;
  }

  const providerFlags = [
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
    <div className="row w-100 mt-2 mb-2">
      <div className="col-12">
          <div className="border rounded bg-white p-3 small position-relative">
          {provider.logo && (
            <a
              href={provider.logo}
              target="_blank"
              rel="noreferrer"
              className="position-absolute top-0 end-0 m-2"
            >
              <img
                src={provider.logo}
                alt={`${provider.name} logo`}
                style={{ maxHeight: "48px", maxWidth: "96px", objectFit: "contain" }}
              />
            </a>
          )}
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <strong>{provider.name}</strong>
            <span className="badge text-bg-secondary">v{provider.version}</span>
            <span className="badge text-bg-info">{provider.status}</span>
            <span className="badge text-bg-light border">#{provider.id}</span>
          </div>

          <div className="row g-2">
            <div className="col-md-6">
              <div>
                <strong>Slug:</strong> {provider.rfc1034CompliantName}
              </div>
              <div>
                <strong>Default model:</strong> {provider.defaultModel}
              </div>
              <div>
                <strong>API key:</strong> {provider.apiKey.name} (#
                {provider.apiKey.id})
              </div>
              <div>
                <strong>Connectivity path:</strong>{" "}
                {provider.connectivityTestPath}
              </div>
              <div>
                <strong>Account:</strong>{" "}
                {provider.userProfile.account.accountNumber}
              </div>
              <div>
                <strong>User:</strong> {provider.userProfile.user.username} (
                {provider.userProfile.user.email})
              </div>
            </div>

            <div className="col-md-6">
              <div>
                <strong>TOS accepted:</strong>{" "}
                {provider.tosAccepted ? "Yes" : "No"}
              </div>
              <div>
                <strong>TOS accepted by:</strong>{" "}
                {provider.tosAcceptedBy.username} (
                {provider.tosAcceptedBy.email})
              </div>
              <div>
                <strong>TOS accepted at:</strong> {provider.tosAcceptedAt}
              </div>
              <div>
                <strong>Ownership requested:</strong>{" "}
                {provider.ownershipRequested ?? "None"}
              </div>
              <div>
                <strong>Created:</strong> {provider.createdAt}
              </div>
              <div>
                <strong>Updated:</strong> {provider.updatedAt}
              </div>
            </div>
          </div>

          <div className="mt-2">
            <strong>Flags:</strong>{" "}
            {providerFlags.map((flag) => (
              <span
                key={flag.label}
                className={`badge me-1 ${flag.enabled ? "text-bg-success" : "text-bg-light border"}`}
              >
                {flag.label}
              </span>
            ))}
          </div>

          <div className="mt-2">
            <strong>Tags:</strong>{" "}
            {provider.tags.length > 0 ? provider.tags.join(", ") : "None"}
          </div>

          <div>
            <strong>Annotations:</strong>{" "}
            {provider.annotations.length > 0
              ? provider.annotations.join(", ")
              : "None"}
          </div>

          <div className="mt-2">
            <strong>Contact:</strong> {provider.contactEmail} (
            {provider.contactEmailVerified}) | <strong>Support:</strong>{" "}
            {provider.supportEmail} ({provider.supportEmailVerified})
          </div>

          <div className="mt-2 d-flex flex-wrap gap-3">
            <a href={provider.websiteUrl} target="_blank" rel="noreferrer">
              Website
            </a>
            <a href={provider.docsUrl} target="_blank" rel="noreferrer">
              Docs
            </a>
            <a
              href={provider.termsOfServiceUrl}
              target="_blank"
              rel="noreferrer"
            >
              Terms
            </a>
            <a
              href={provider.privacyPolicyUrl}
              target="_blank"
              rel="noreferrer"
            >
              Privacy
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
