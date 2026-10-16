import type { LLMProvider } from "@/components/LLMProviders";
import { gettext } from "@smarter/common";

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
            <strong>{gettext("Slug:")}</strong> {provider.rfc1034CompliantName}
          </div>
          <div>
            <strong>{gettext("Default model:")}</strong> {provider.defaultModel}
          </div>
          <div>
            <strong>{gettext("API Key Secret Name:")}</strong> {provider.apiKey.name}
          </div>
          <div>
            <strong>{gettext("Connectivity path:")}</strong> {provider.connectivityTestPath}
          </div>
          <div>
            <strong>{gettext("Account:")}</strong> {provider.userProfile.account.accountNumber}
          </div>
          <div>
            <strong>{gettext("User:")}</strong> {provider.userProfile.user.username} ({provider.userProfile.user.email})
          </div>
        </div>

        <div className="col-md-6">
          <div>
            <strong>{gettext("TOS accepted:")}</strong> {provider.tosAccepted ? gettext("Yes") : gettext("No")}
          </div>
          <div>
            <strong>{gettext("TOS accepted by:")}</strong> {provider.tosAcceptedBy.username} (
            {provider.tosAcceptedBy.email})
          </div>
          <div>
            <strong>{gettext("TOS accepted at:")}</strong> {formatDate(provider.tosAcceptedAt)}
          </div>
          <div>
            <strong>{gettext("Ownership requested:")}</strong> {provider.ownershipRequested ?? gettext("None")}
          </div>
          <div>
            <strong>{gettext("Created:")}</strong> {formatDate(provider.createdAt)}
          </div>
          <div>
            <strong>{gettext("Updated:")}</strong> {formatDate(provider.updatedAt)}
          </div>
        </div>
      </div>

      <div className="mt-2">
        <strong>{gettext("Tags:")}</strong> {provider.tags.length > 0 ? provider.tags.join(", ") : gettext("None")}
      </div>

      <div>
        <strong>{gettext("Annotations:")}</strong>{" "}
        {provider.annotations.length > 0 ? provider.annotations.join(", ") : gettext("None")}
      </div>

      <div className="mt-2">
        <strong>{gettext("Contact:")}</strong> {provider.contactEmail} ({formatDate(provider.contactEmailVerified)}) |{" "}
        <strong>{gettext("Support:")}</strong> {provider.supportEmail} ({formatDate(provider.supportEmailVerified)})
      </div>
    </>
  );
}
