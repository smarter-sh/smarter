import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SecureUrl from "@/components/SecureUrl";
import { authenticatedPage, publicPage, session, workbenchPage } from "@/mocks/fixtures";

const noop = () => {};

describe("SecureUrl", () => {
  it("explains the commands and the manifest on the public page", () => {
    render(<SecureUrl page={publicPage} session={null} onPage={noop} />);
    expect(screen.getByRole("heading", { name: "Create an api key" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Attach it to this LLMClient" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Give it to Smarter Chat" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "manifest.yaml" })).toHaveTextContent("apiKey: <API-KEY-NAME>");
    expect(screen.getByRole("link", { name: "API Keys" })).not.toHaveAttribute("target");
    expect(screen.queryByText("You can do it right here.", { exact: false })).not.toBeInTheDocument();
    expect(screen.getByText(/Right now, anyone who has this url/)).toBeInTheDocument();
  });

  it("manages the api key in place in the workbench", () => {
    render(<SecureUrl page={workbenchPage} session={session} onPage={noop} />);
    expect(screen.getByRole("heading", { name: "Choose its api key" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Give it to Smarter Chat" })).toBeInTheDocument();
    expect(screen.getByText(/You can do it right here\./)).toBeInTheDocument();
  });

  it("says that the url already requires an api key", () => {
    render(<SecureUrl page={authenticatedPage} session={session} onPage={noop} />);
    expect(screen.getByText(/already requires an api key/)).toBeInTheDocument();
  });
});
