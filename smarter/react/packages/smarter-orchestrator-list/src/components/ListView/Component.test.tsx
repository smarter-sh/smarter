import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";

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

  const manyObjects = Array.from({ length: 12 }, (_, idx) => makeObject(100 + idx));

  function renderMany() {
    return render(
      <ListView
        isLoading={false}
        ghostRows={3}
        sessionContext={sessionContext}
        objects={manyObjects}
        onRequery={() => {}}
      />,
    );
  }

  it("renders a long list in chunks", async () => {
    renderMany();
    // the header row, and the first chunk of rows, then the rest.
    expect(screen.getAllByRole("row")).toHaveLength(1 + 5);
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(1 + manyObjects.length));
  });

  it("schedules the chunks with requestIdleCallback when the browser has it", async () => {
    const cancelIdleCallback = vi.fn();
    vi.stubGlobal("requestIdleCallback", (callback: () => void) => setTimeout(callback, 0));
    vi.stubGlobal("cancelIdleCallback", cancelIdleCallback);
    try {
      const { unmount } = renderMany();
      await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(1 + manyObjects.length));
      unmount();
      expect(cancelIdleCallback).toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("logs a list that isn't an array", () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    render(
      <ListView
        isLoading
        ghostRows={1}
        sessionContext={sessionContext}
        objects={undefined as never}
        onRequery={() => {}}
      />,
    );
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("objects length: N/A"));
  });
});
