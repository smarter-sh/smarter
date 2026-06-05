import type { LLMProvider } from "../LLMProviders";

const DATE_FORMAT: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZoneName: "short",
};

function formatDate(value: string): string {
  const d = new Date(value.replace(/(\.\d{3})\d+/, "$1"));
  return isNaN(d.getTime()) ? value : d.toLocaleString("en-US", DATE_FORMAT);
}

interface ProviderDetailsProps {
  provider: LLMProvider;
}

export default function ProviderDetails({ provider }: ProviderDetailsProps) {
  return (
    <>
      <div className="row g-2">
        <div className="col-md-6">
          <div>
            <strong>Slug:</strong> {provider.rfc1034CompliantName}
          </div>
          <div>
            <strong>Default model:</strong> {provider.defaultModel}
          </div>
          <div>
            <strong>API Key Secret Name:</strong> {provider.apiKey.name}
          </div>
          <div>
            <strong>Connectivity path:</strong> {provider.connectivityTestPath}
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
            <strong>TOS accepted:</strong> {provider.tosAccepted ? "Yes" : "No"}
          </div>
          <div>
            <strong>TOS accepted by:</strong> {provider.tosAcceptedBy.username}{" "}
            ({provider.tosAcceptedBy.email})
          </div>
          <div>
            <strong>TOS accepted at:</strong>{" "}
            {formatDate(provider.tosAcceptedAt)}
          </div>
          <div>
            <strong>Ownership requested:</strong>{" "}
            {provider.ownershipRequested ?? "None"}
          </div>
          <div>
            <strong>Created:</strong>{" "}
            {formatDate(provider.createdAt)}
          </div>
          <div>
            <strong>Updated:</strong>{" "}
            {formatDate(provider.updatedAt)}
          </div>
        </div>
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
        {formatDate(provider.contactEmailVerified)}) | <strong>Support:</strong>{" "}
        {provider.supportEmail} ({formatDate(provider.supportEmailVerified)})
      </div>
    </>
  );
}
