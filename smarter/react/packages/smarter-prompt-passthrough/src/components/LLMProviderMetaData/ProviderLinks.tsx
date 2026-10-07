import type { LLMProvider } from "../LLMProviders";

interface ProviderLinksProps {
  provider: LLMProvider;
}

export default function ProviderLinks({ provider }: ProviderLinksProps) {
  return (
    <div className="mt-2 mb-2 d-flex flex-wrap gap-3">
      <a href={provider.websiteUrl} target="_blank" rel="noreferrer">
        Website
      </a>
      <a href={provider.docsUrl} target="_blank" rel="noreferrer">
        Docs
      </a>
      <a href={provider.termsOfServiceUrl} target="_blank" rel="noreferrer">
        Terms
      </a>
      <a href={provider.privacyPolicyUrl} target="_blank" rel="noreferrer">
        Privacy
      </a>
    </div>
  );
}
