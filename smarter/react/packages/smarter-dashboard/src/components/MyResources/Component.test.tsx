import { render, screen } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, myResources } from "@/mocks/fixtures";
import { server } from "@test/server";

import MyResources from "./Component";

const apiUrl = appContext.myResourcesApiUrl;

describe("MyResources", () => {
  it("counts a single pending deployment", async () => {
    server.use(http.post(apiUrl, () => HttpResponse.json({ ...myResources, pending_deployments: 1 })));
    render(<MyResources apiUrl={apiUrl} />);
    expect(await screen.findByRole("link", { name: "1 pending" })).toBeInTheDocument();
    expect(screen.getByText(/^\s*deployment$/)).toBeInTheDocument();
  });

  it("counts nothing for a response without counts", async () => {
    server.use(http.post(apiUrl, () => HttpResponse.json({})));
    render(<MyResources apiUrl={apiUrl} />);
    await vi.waitFor(() => expect(screen.queryByText(/pending/)).not.toBeInTheDocument());
    expect(screen.getByRole("region", { name: "My Resources" })).toBeInTheDocument();
  });

  it("shows why the resources failed to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(apiUrl, () => new HttpResponse(null, { status: 503 })));
    render(<MyResources apiUrl={apiUrl} />);
    expect(await screen.findByText("Failed to load resources: Request failed: 503")).toBeInTheDocument();
  });

  it("stops loading when it unmounts", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(
      http.post(apiUrl, async () => {
        await delay("infinite");
        return HttpResponse.json(myResources);
      }),
    );
    const { unmount } = render(<MyResources apiUrl={apiUrl} />);
    unmount();
    await vi.waitFor(() =>
      expect(error).toHaveBeenCalledWith(expect.anything(), "Error loading My Resources:", expect.anything()),
    );
  });
});
