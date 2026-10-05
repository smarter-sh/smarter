import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ownedObjects, sessionContext } from "@/mocks/fixtures";

import ListView from "./Component";

describe("ListView", () => {
  it("shows a row for each object", async () => {
    render(
      <ListView
        isLoading={false}
        ghostRows={3}
        sessionContext={sessionContext}
        objects={ownedObjects}
        onRequery={() => {}}
      />,
    );
    for (const object of ownedObjects) {
      expect(await screen.findByRole("row", { name: new RegExp(object.name) })).toBeInTheDocument();
    }
  });

  it("shows skeleton rows while loading", () => {
    render(<ListView isLoading ghostRows={4} sessionContext={sessionContext} objects={[]} onRequery={() => {}} />);
    // the header row, and a skeleton row for each of the ghostRows.
    expect(screen.getAllByRole("row")).toHaveLength(1 + 4);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
