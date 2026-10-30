/**
 * ExtensionDetailView React Component
 *
 * The Details tab of an Extension's detail, which the Extensions tab opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common). It is read-only, without a Toolbar: superusers manage
 * extensions in the Extensions console. An Extension is not a SAM resource, so its detail has only this tab.
 *
 * It shows the extension's description and status, then what it is and who publishes it, and how it is installed.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context.
 * - object (Extension): The extension.
 *
 * Usage:
 * <ExtensionDetailView sessionContext={sessionContext} object={extension} onRequery={onRequery} />
 */
import { DetailField, DetailOverview, DetailSection, gettext } from "@smarter/common";

import type { ExtensionDetailViewProps } from "@/lib/Types";
import { ExtensionStatusBar } from "@/components/ExtensionStatusBar";

function ExtensionDetailView({ object: extension }: ExtensionDetailViewProps) {
  return (
    <>
      <DetailOverview description={extension.description}>
        <span
          className={`badge ${extension.enabled ? "badge-light-success" : "badge-light"} fw-semibold`}
          title={gettext("Whether the extension's tools are offered to LLMs. A platform administrator enables it.")}
        >
          {extension.enabled ? gettext("Enabled") : gettext("Disabled")}
        </span>
        <ExtensionStatusBar extension={extension} />
      </DetailOverview>

      <DetailSection title={gettext("Extension")} icon="technology-4">
        <DetailField label={gettext("Name")} value={extension.displayName} />
        <DetailField
          label={gettext("Slug")}
          value={extension.slug}
          type="code"
          help={gettext("An LLMClient manifest lists the extension by its slug, under spec.extensions.")}
        />
        <DetailField
          label={gettext("Version")}
          value={extension.version}
          type="code"
          help={gettext("The installed version.")}
        />
        <DetailField
          label={gettext("Publisher")}
          value={extension.publisher}
          help={gettext("The publisher's registry id, or an uploaded archive's authors.")}
        />
        <DetailField label={gettext("License")} value={extension.license} type="code" />
        <DetailField label={gettext("Homepage")} value={extension.homepage} type="url" />
      </DetailSection>

      <DetailSection title={gettext("Installation")} icon="cloud-download">
        <DetailField
          label={gettext("Trust badge")}
          value={extension.trustBadgeLabel}
          help={gettext("How far the extension is trusted: official, verified, community, or unverified.")}
        />
        <DetailField
          label={gettext("Source")}
          value={
            extension.source === "registry" ? gettext("The Smarter Extension registry") : gettext("An uploaded archive")
          }
        />
        <DetailField label={gettext("ID")} value={extension.id} type="code" />
        <DetailField label={gettext("Installed")} value={extension.createdAt} type="dateTime" />
        <DetailField label={gettext("Last updated")} value={extension.updatedAt} type="dateTime" />
      </DetailSection>
    </>
  );
}

export default ExtensionDetailView;
