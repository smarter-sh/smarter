import type { LLMProvider } from "@/components/LLMProviders";
import { gettext, interpolate } from "@smarter/common";

interface ProviderFlagsProps {
  provider: LLMProvider;
}

interface Flag {
  label: string;
  enabled: boolean;
  /** A flag that's bad news when it's set: deprecated, flagged or suspended. */
  warning?: boolean;
}

/**
 * The provider's flags, as a row of chips. A flag that's set is green, or red when it's bad news; one
 * that isn't is a faint gray chip, so that the row always shows all eight, in the same order.
 */
export default function ProviderFlags({ provider }: ProviderFlagsProps) {
  const flags: Flag[] = [
    { label: gettext("Active"), enabled: provider.isActive },
    { label: gettext("Default"), enabled: provider.isDefault },
    { label: gettext("Verified"), enabled: provider.isVerified },
    { label: gettext("Featured"), enabled: provider.isFeatured },
    { label: gettext("Official"), enabled: provider.isOfficialProvider },
    { label: gettext("Deprecated"), enabled: provider.isDeprecated, warning: true },
    { label: gettext("Flagged"), enabled: provider.isFlagged, warning: true },
    { label: gettext("Suspended"), enabled: provider.isSuspended, warning: true },
  ];

  return (
    <ul className="provider-meta-flags" aria-label={gettext("Flags")}>
      {flags.map((flag) => {
        const state = flag.enabled
          ? // Translators: a provider flag that is set, e.g. "Featured: yes".
            interpolate(gettext("%(flag)s: yes"), { flag: flag.label })
          : // Translators: a provider flag that isn't set, e.g. "Featured: no".
            interpolate(gettext("%(flag)s: no"), { flag: flag.label });
        const tone = !flag.enabled ? "off" : flag.warning ? "warning" : "on";
        const icon = !flag.enabled ? "ki-minus" : flag.warning ? "ki-information" : "ki-check";
        return (
          <li key={flag.label} className={`provider-meta-flag provider-meta-flag-${tone}`} title={state}>
            <i className={`ki-outline ${icon} fs-7 me-1`} aria-hidden="true"></i>
            <span aria-hidden="true">{flag.label}</span>
            <span className="visually-hidden">{state}</span>
          </li>
        );
      })}
    </ul>
  );
}
