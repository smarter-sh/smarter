import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AppTitle from "@/components/AppTitle/Component";

describe("AppTitle", () => {
  it("shows a valid LLMClient in the sandbox", () => {
    render(<AppTitle title="Stackademy v1.0.0" isReady isValid isDeployed={false} />);
    expect(screen.getByText("Stackademy v1.0.0")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "valid" })).toBeInTheDocument();
    expect(screen.getByText("(sandbox)")).toBeInTheDocument();
  });

  it("shows a deployed LLMClient that is not valid", () => {
    render(<AppTitle title="Stackademy v1.0.0" isReady isValid={false} isDeployed />);
    expect(screen.getByRole("img", { name: "not valid" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "deployed" })).toBeInTheDocument();
    expect(screen.queryByText("(sandbox)")).not.toBeInTheDocument();
  });

  it("is loading until it is ready", () => {
    render(<AppTitle title="Stackademy v1.0.0" isReady={false} isValid isDeployed={false} />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });
});
