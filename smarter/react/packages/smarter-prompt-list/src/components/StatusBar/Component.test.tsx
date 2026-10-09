import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";

import { StatusBar } from "./Component";

describe("StatusBar", () => {
  it("shows an LLMClient that isn't ready, deployed, verified or certified", () => {
    render(<StatusBar llmclient={makeObject(1, { ready: false })} />);
    expect(screen.getByTitle("Not ready: LLMClient is initializing")).toBeInTheDocument();
    expect(screen.getByTitle("Not deployed")).toBeInTheDocument();
    expect(screen.getByTitle("No authentication required")).toBeInTheDocument();
    expect(screen.getByTitle("DNS verification pending or failed")).toBeInTheDocument();
    expect(screen.getByTitle("TLS certificate pending or failed")).toBeInTheDocument();
    expect(screen.queryByTitle(/^Subdomain:/)).not.toBeInTheDocument();
    expect(screen.queryByTitle(/^Custom domain:/)).not.toBeInTheDocument();
  });

  it("shows a ready, deployed LLMClient, with its domains", () => {
    const llmclient = makeObject(1, {
      ready: true,
      deployed: true,
      isAuthenticationRequired: true,
      dnsVerificationStatus: "verified",
      tlsCertificateIssuanceStatus: "issued",
      subdomain: "example",
      customDomain: "example.com",
    } as Partial<ReturnType<typeof makeObject>>);
    render(<StatusBar llmclient={llmclient} />);
    expect(screen.getByTitle("Ready: LLMClient is ready to serve requests")).toBeInTheDocument();
    expect(screen.getByTitle("Deployed: LLMClient is deployed")).toBeInTheDocument();
    expect(screen.getByTitle("Authentication required to access this llmclient")).toBeInTheDocument();
    expect(screen.getByTitle("DNS verified")).toBeInTheDocument();
    expect(screen.getByTitle("TLS certificate issued")).toBeInTheDocument();
    expect(screen.getByTitle("Subdomain: example")).toBeInTheDocument();
    expect(screen.getByTitle("Custom domain: example.com")).toBeInTheDocument();
  });
});
