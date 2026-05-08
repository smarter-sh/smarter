import type { LLMProvider } from "../LLMProviders";
import ProviderDetails from "./ProviderDetails";
import ProviderFlags from "./ProviderFlags";
import ProviderLinks from "./ProviderLinks";

interface ProviderMetaDataProps {
  provider: LLMProvider | null;
}

export default function LLMProviderMetaData({ provider }: ProviderMetaDataProps) {
  if (!provider) {
    return null;
  }

  return (
    <div className="row w-100 mt-2 mb-2">
      <div className="col-12">
          <div className="border rounded bg-white p-3 small position-relative">
          {provider.logo && (
            <a
              href={provider.logo}
              target="_blank"
              rel="noreferrer"
              className="position-absolute top-0 end-0 m-2 bg-light border rounded p-1"
            >
              <img
                src={provider.logo}
                alt={`${provider.name} logo`}
                style={{ maxHeight: "48px", maxWidth: "96px", objectFit: "contain" }}
              />
            </a>
          )}
          <ProviderLinks provider={provider} />
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <h4>
              <strong>{provider.name}</strong>
              <span className="badge text-bg-secondary">v{provider.version}</span>
              <span className="badge text-bg-info">{provider.status}</span>
            </h4>
          </div>
          <ProviderFlags provider={provider} />
          <ProviderDetails provider={provider} />
        </div>
      </div>
    </div>
  );
}
