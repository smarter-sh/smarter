import type { LLMProvider } from "@/components/LLMProviders";
import { gettext } from "@smarter/common";

interface ProviderLinksProps {
  provider: LLMProvider;
}

/** The provider's own pages, each a small button that opens in a new tab. A page the provider doesn't have is left out. */
export default function ProviderLinks({ provider }: ProviderLinksProps) {
  const links = [
    { label: gettext("Website"), icon: "ki-home", url: provider.websiteUrl },
    { label: gettext("Docs"), icon: "ki-book-open", url: provider.docsUrl },
    { label: gettext("Terms"), icon: "ki-document", url: provider.termsOfServiceUrl },
    { label: gettext("Privacy"), icon: "ki-lock", url: provider.privacyPolicyUrl },
  ].filter((link) => link.url);

  if (links.length === 0) {
    return null;
  }

  return (
    <nav className="d-flex flex-wrap gap-2" aria-label={gettext("Provider links")}>
      {links.map((link) => (
        <a
          key={link.label}
          href={link.url!}
          target="_blank"
          rel="noreferrer"
          className="btn btn-sm btn-light btn-active-light-primary px-3 py-2"
        >
          <i className={`ki-outline ${link.icon} fs-5 me-1`}></i>
          {link.label}
        </a>
      ))}
    </nav>
  );
}
