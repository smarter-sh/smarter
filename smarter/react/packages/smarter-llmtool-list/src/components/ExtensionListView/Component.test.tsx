import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { extensionObjects, makeExtension, sessionContext } from "@/mocks/fixtures";

import ExtensionListView from "@/components/ExtensionListView/Component";

describe("ExtensionListView", () => {
  it("shows a read-only row for each extension, linked to its homepage when it has one", async () => {
    render(
      <ExtensionListView
        isLoading={false}
        ghostRows={3}
        sessionContext={sessionContext}
        objects={extensionObjects}
        onRequery={() => {}}
      />,
    );
    const weather = await screen.findByRole("row", { name: /Weather/ });
    expect(within(weather).getByRole("link", { name: "Weather" })).toHaveAttribute(
      "href",
      extensionObjects[0].homepage,
    );
    expect(within(weather).getByText("weather")).toBeInTheDocument();
    expect(within(weather).queryByRole("button")).not.toBeInTheDocument();

    const calculator = screen.getByRole("row", { name: /Calculator/ });
    expect(within(calculator).queryByRole("link")).not.toBeInTheDocument();
    expect(within(calculator).getByTitle(/^Disabled:/)).toBeInTheDocument();
    expect(within(calculator).getByTitle("Unverified")).toBeInTheDocument();
    expect(within(calculator).getByTitle("Installed from an upload")).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Operations" })).not.toBeInTheDocument();
  });

  it("shows skeleton rows while loading", () => {
    render(
      <ExtensionListView isLoading ghostRows={4} sessionContext={sessionContext} objects={[]} onRequery={() => {}} />,
    );
    // the header row, and a skeleton row for each of the ghostRows.
    expect(screen.getAllByRole("row")).toHaveLength(1 + 4);
  });

  const manyExtensions = Array.from({ length: 12 }, (_, idx) => makeExtension(100 + idx));

  it("renders a long list in chunks", async () => {
    render(
      <ExtensionListView
        isLoading={false}
        ghostRows={3}
        sessionContext={sessionContext}
        objects={manyExtensions}
        onRequery={() => {}}
      />,
    );
    expect(screen.getAllByRole("row")).toHaveLength(1 + 5);
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(1 + manyExtensions.length));
  });

  it("schedules the chunks with requestIdleCallback when the browser has it", async () => {
    const cancelIdleCallback = vi.fn();
    vi.stubGlobal("requestIdleCallback", (callback: () => void) => setTimeout(callback, 0));
    vi.stubGlobal("cancelIdleCallback", cancelIdleCallback);
    try {
      const { unmount } = render(
        <ExtensionListView
          isLoading={false}
          ghostRows={3}
          sessionContext={sessionContext}
          objects={manyExtensions}
          onRequery={() => {}}
        />,
      );
      await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(1 + manyExtensions.length));
      unmount();
      expect(cancelIdleCallback).toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("logs a list that isn't an array", () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    render(
      <ExtensionListView
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
