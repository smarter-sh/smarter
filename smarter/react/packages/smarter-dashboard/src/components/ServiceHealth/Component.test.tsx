import { render, screen } from "@testing-library/react";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { appContext, serviceHealth } from "@/mocks/fixtures";
import { server } from "@test/server";

import ServiceHealth from "./Component";

const apiUrl = appContext.serviceHealthApiUrl;

describe("ServiceHealth", () => {
  it("shows why the service health failed to load", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(http.post(apiUrl, () => new HttpResponse(null, { status: 503 })));
    render(<ServiceHealth apiUrl={apiUrl} />);
    expect(await screen.findByText(/Request failed: 503/)).toBeInTheDocument();
  });

  it("stops loading when it unmounts", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    server.use(
      http.post(apiUrl, async () => {
        await delay("infinite");
        return HttpResponse.json(serviceHealth);
      }),
    );
    const { unmount } = render(<ServiceHealth apiUrl={apiUrl} />);
    unmount();
    await vi.waitFor(() =>
      expect(error).toHaveBeenCalledWith(expect.anything(), "Error loading Service Health:", expect.anything()),
    );
  });
});
