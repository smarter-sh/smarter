import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";
import type { CustomDomain } from "@/lib/Types";

import { StatusBar } from "./Component";
import { VerificationBadge } from "./VerificationBadge";

const llmclient = { name: "example_llmclient", deployed: true } as CustomDomain["llmclient"];

describe("StatusBar", () => {
  it("shows a domain that no LLMClient uses", () => {
    render(<StatusBar customDomain={makeObject(1)} />);
    expect(screen.getByTitle("No LLMClient uses this domain")).toBeInTheDocument();
    expect(screen.getByTitle("Not deployed")).toBeInTheDocument();
    expect(screen.getByTitle("1 DNS record")).toBeInTheDocument();
  });

  it("shows the deployed LLMClient that uses the domain", () => {
    render(<StatusBar customDomain={makeObject(1, { llmclient, dnsRecords: undefined as never })} />);
    expect(screen.getByTitle("LLMClient: example_llmclient")).toBeInTheDocument();
    expect(screen.getByTitle("Deployed: the LLMClient is deployed")).toBeInTheDocument();
    expect(screen.getByTitle("0 DNS records")).toBeInTheDocument();
  });
});

describe("VerificationBadge", () => {
  it("shows when a verified domain was verified", () => {
    render(<VerificationBadge customDomain={makeObject(1)} />);
    expect(screen.getByText("Verified")).toHaveAttribute(
      "title",
      expect.stringMatching(/^Verified .*: DNS is delegated/),
    );
  });

  it("shows a spinner while verifying, with the verification message", () => {
    render(
      <VerificationBadge
        customDomain={makeObject(1, { verificationStatus: "Verifying", verificationMessage: "Waiting." })}
      />,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByTitle("Waiting.")).toHaveTextContent("Verifying");
  });

  it("treats a domain without a status as not verified", () => {
    render(<VerificationBadge customDomain={makeObject(1, { verificationStatus: "" as never, verifiedAt: null })} />);
    expect(screen.getByTitle("Not verified: deploy the custom domain to verify it")).toHaveTextContent("Not Verified");
  });

  it("styles an unknown status as not verified", () => {
    render(<VerificationBadge customDomain={makeObject(1, { verificationStatus: "Unknown" as never })} />);
    expect(screen.getByText("Unknown")).toHaveClass("badge-light-secondary");
  });
});
