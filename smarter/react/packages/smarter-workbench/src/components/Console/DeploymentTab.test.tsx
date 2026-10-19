import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DeploymentTab from "@/components/Console/DeploymentTab";
import { workbench } from "@/mocks/fixtures";
import { tabErrorHandlers, tabHandlers } from "@/mocks/handlers";
import { server } from "@test/server";

describe("DeploymentTab", () => {
  it("fetches the deployment page, and shows it in its workbench mode", async () => {
    server.use(...tabHandlers);
    render(<DeploymentTab workbench={workbench} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Deployed" })).toBeInTheDocument();
    // the workbench's own sections: the owner, and the api keys, which it manages with its session.
    expect(screen.getByRole("rowheader", { name: "Owner" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Choose its api key" })).toBeInTheDocument();
  });

  it("says why the page couldn't load", async () => {
    server.use(...tabErrorHandlers);
    render(<DeploymentTab workbench={workbench} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The request failed: 404 Not Found");
  });
});
