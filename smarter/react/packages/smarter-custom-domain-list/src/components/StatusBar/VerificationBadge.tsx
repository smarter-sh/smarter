/**
 * VerificationBadge React component: the verification status of a CustomDomain, as a colored badge.
 *
 * A custom domain is Verified when its NS records are delegated to Smarter, and its TLS
 * certificate is issued. The badge's tooltip says when it was verified, or why it is
 * not verified yet.
 *
 * Usage:
 *   <VerificationBadge customDomain={customDomain} />
 */
import { formatDateTime, gettext, interpolate } from "@smarter/common";

import type { CustomDomain, CustomDomainVerificationStatus } from "@/lib/Types";

const BADGE_CLASSES: Record<CustomDomainVerificationStatus, string> = {
  "Not Verified": "badge badge-light-secondary text-gray-700",
  Verifying: "badge badge-light-warning",
  Verified: "badge badge-light-success",
  Failed: "badge badge-light-danger",
};

/** The verification status, in the language of the page. A status that this app doesn't know is shown as it is. */
const statusLabel = (status: CustomDomainVerificationStatus): string => {
  switch (status) {
    case "Verifying":
      return gettext("Verifying");
    case "Verified":
      return gettext("Verified");
    case "Failed":
      return gettext("Failed");
    case "Not Verified":
      return gettext("Not Verified");
    default:
      return status;
  }
};

export const VerificationBadge = ({ customDomain }: { customDomain: CustomDomain }) => {
  const status = customDomain.verificationStatus || "Not Verified";
  const title =
    status === "Verified" && customDomain.verifiedAt
      ? interpolate(gettext("Verified %(dateTime)s: DNS is delegated, and the TLS certificate is issued"), {
          dateTime: formatDateTime(customDomain.verifiedAt),
        })
      : customDomain.verificationMessage || gettext("Not verified: deploy the custom domain to verify it");
  return (
    <span className={BADGE_CLASSES[status] || BADGE_CLASSES["Not Verified"]} title={title}>
      {status === "Verifying" && <span className="spinner-border spinner-border-sm me-1" role="status" />}
      {statusLabel(status)}
    </span>
  );
};
