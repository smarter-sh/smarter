import { render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";

import ListView from "@/components/ListView/Component";

describe("ListView", () => {
  it("shows a row for each object", async () => {
    render(<ListView isLoading={false} sessionContext={sessionContext} objects={ownedObjects} onRequery={() => {}} />);
    for (const object of ownedObjects) {
      expect(await screen.findByRole("row", { name: new RegExp(object.name) })).toBeInTheDocument();
    }
  });

  it("marks the Get Weather LLMClient's name for the onboarding hint, and no other", async () => {
    const weather = { ...makeObject(200), name: "weather" };
    render(
      <ListView
        isLoading={false}
        sessionContext={sessionContext}
        objects={[weather, ...ownedObjects]}
        onRequery={() => {}}
      />,
    );
    expect(await screen.findByText("weather")).toHaveAttribute("data-smarter-onboarding", "llmclient-weather");
    expect(screen.getByText(ownedObjects[0].name)).not.toHaveAttribute("data-smarter-onboarding");
  });

  it("shows the name as text, since the row opens the llmclient's detail", async () => {
    render(<ListView isLoading={false} sessionContext={sessionContext} objects={ownedObjects} onRequery={() => {}} />);
    const name = await screen.findByText(ownedObjects[0].name);
    expect(name.tagName).toBe("SPAN");
    // the Toolbar's Chat button still opens its chat.
    const row = within(screen.getByRole("row", { name: new RegExp(ownedObjects[0].name) }));
    expect(row.getByTitle("Chat: Open the prompt workbench")).toHaveAttribute("href", ownedObjects[0].urlChatapp);
  });

  it("shows skeleton rows while loading", () => {
    render(<ListView isLoading sessionContext={sessionContext} objects={[]} onRequery={() => {}} />);
    // the header row, and a skeleton row for each of the ghostRows.
    expect(screen.getAllByRole("row")).toHaveLength(1 + 5);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  const manyObjects = Array.from({ length: 12 }, (_, idx) => makeObject(100 + idx));

  function renderMany() {
    return render(
      <ListView isLoading={false} sessionContext={sessionContext} objects={manyObjects} onRequery={() => {}} />,
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

  it("shows an LLMClient's tools", async () => {
    render(
      <ListView isLoading={false} sessionContext={sessionContext} objects={[makeObject(1)]} onRequery={() => {}} />,
    );
    const row = await screen.findByRole("row", { name: /example_1/ });
    expect(row).toHaveTextContent(
      "get_current_weather, example_configuration, everlasting_gobstopper, example_mcpclient",
    );
  });

  it("shows the default model, and an LLMClient without tools", async () => {
    const llmclient = makeObject(1, {
      defaultModel: "",
      tools: undefined,
    } as unknown as Partial<ReturnType<typeof makeObject>>);
    render(<ListView isLoading={false} sessionContext={sessionContext} objects={[llmclient]} onRequery={() => {}} />);
    const row = await screen.findByRole("row", { name: /example_1/ });
    expect(row).toHaveTextContent("default");
  });

  it("logs a list that isn't an array", () => {
    const debug = vi.spyOn(console, "debug").mockImplementation(() => {});
    render(<ListView isLoading sessionContext={sessionContext} objects={undefined as never} onRequery={() => {}} />);
    expect(debug).toHaveBeenCalledWith(expect.stringContaining("objects length: N/A"));
  });
});
