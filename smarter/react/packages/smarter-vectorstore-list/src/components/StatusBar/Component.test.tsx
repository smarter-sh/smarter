import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeObject } from "@/mocks/fixtures";

import { StatusBar } from "@/components/StatusBar/Component";

describe("StatusBar", () => {
  it("shows a ready vectorstore, and its scheduled snapshots", () => {
    render(<StatusBar vectorstore={makeObject(1)} />);
    expect(screen.getByText("Ready")).toHaveAttribute("title", "Its database is serving.");
    expect(screen.getByTitle("Scheduled snapshots: 1 kept.")).toBeInTheDocument();
    expect(screen.queryByTitle(/^Inactive/)).not.toBeInTheDocument();
    expect(screen.queryByTitle(/^Deletion protection/)).not.toBeInTheDocument();
  });

  it("shows an inactive, protected vectorstore with its status message and last snapshot", () => {
    render(
      <StatusBar
        vectorstore={makeObject(1, {
          status: "failed",
          statusMessage: "Out of disk.",
          isActive: false,
          deletionProtection: true,
          lastSnapshotAt: "2026-06-20",
        })}
      />,
    );
    expect(screen.getByText("Failed")).toHaveAttribute("title", "See its status message. Out of disk.");
    expect(screen.getByTitle("Inactive: it may not be used.")).toBeInTheDocument();
    expect(screen.getByTitle("Deletion protection: its database cannot be destroyed.")).toBeInTheDocument();
    expect(screen.getByTitle("Scheduled snapshots: 1 kept, the last at 2026-06-20.")).toBeInTheDocument();
  });

  it("shows an unknown status as pending, and no snapshots when they are off", () => {
    render(
      <StatusBar
        vectorstore={makeObject(1, { status: "unknown" as never, spec: { maintenance: { snapshots: false } } })}
      />,
    );
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.queryByTitle(/^Scheduled snapshots/)).not.toBeInTheDocument();
  });

  it("shows a vectorstore without a spec", () => {
    render(<StatusBar vectorstore={makeObject(1, { spec: undefined as never })} />);
    expect(screen.getByTitle(/^Scheduled snapshots/)).toBeInTheDocument();
  });
});
