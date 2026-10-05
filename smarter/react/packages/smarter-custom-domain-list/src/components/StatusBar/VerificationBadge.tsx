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
import { formatDateTime } from "@smarter/common";

import type { CustomDomain, CustomDomainVerificationStatus } from "@/lib/Types";

const BADGE_CLASSES: Record<CustomDomainVerificationStatus, string> = {
  "Not Verified": "badge badge-light-secondary text-gray-700",
  Verifying: "badge badge-light-warning",
  Verified: "badge badge-light-success",
  Failed: "badge badge-light-danger",
};

export const VerificationBadge = ({ customDomain }: { customDomain: CustomDomain }) => {
  const status = customDomain.verificationStatus || "Not Verified";
  const title =
    status === "Verified" && customDomain.verifiedAt
      ? `Verified ${formatDateTime(customDomain.verifiedAt)}: DNS is delegated, and the TLS certificate is issued`
      : customDomain.verificationMessage || "Not verified: deploy the custom domain to verify it";
  return (
    <span className={BADGE_CLASSES[status] || BADGE_CLASSES["Not Verified"]} title={title}>
      {status === "Verifying" && <span className="spinner-border spinner-border-sm me-1" role="status" />}
      {status}
    </span>
  );
};
