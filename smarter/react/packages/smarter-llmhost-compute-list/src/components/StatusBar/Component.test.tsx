import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";
import type { LLMHostCompute } from "@/lib/Types";

import { StatusBar } from "@/components/StatusBar/Component";

const compute = (overrides: Partial<LLMHostCompute>) => makeObject(1, { nodegroupName: "ng", ...overrides });

describe("StatusBar", () => {
  it.each<[Partial<LLMHostCompute>, string]>([
    [{ nodegroupStatus: "absent" }, "No node group yet"],
    [{ nodegroupStatus: "ACTIVE" }, "Node group ng is active."],
    [{ nodegroupStatus: "ACTIVE", statusMessage: "All good." }, "Node group ng is active. All good."],
    [{ nodegroupStatus: "CREATING" }, "Node group ng is creating."],
    [{ nodegroupStatus: "UPDATING", statusMessage: "Scaling." }, "Node group ng is updating. Scaling."],
    [{ nodegroupStatus: "DELETING" }, "Node group ng is being deleted."],
    [
      { nodegroupStatus: "CREATE_FAILED", statusMessage: "No capacity." },
      "Node group ng is CREATE_FAILED. No capacity.",
    ],
  ])("describes the node group of %j", (overrides, title) => {
    render(<StatusBar compute={compute(overrides)} />);
    expect(screen.getByTitle(new RegExp(`^${title.replace(/\./g, "\\.")}`))).toBeInTheDocument();
  });

  it("says when nodes are starting", () => {
    render(<StatusBar compute={compute({ desiredNodes: 2, readyNodes: 1 })} />);
    expect(screen.getByTitle(/Nodes are starting\.$/)).toHaveTextContent("1/2");
  });

  it("shows ready nodes, and a compute that no LLMHost uses", () => {
    render(<StatusBar compute={compute({ desiredNodes: 1, readyNodes: 1, llmhostCount: 0 })} />);
    expect(screen.getByTitle(/^Nodes: /)).not.toHaveAttribute("title", expect.stringContaining("starting"));
    expect(screen.getByTitle("LLMHosts that run on it: 0")).toHaveTextContent("0");
  });
});
