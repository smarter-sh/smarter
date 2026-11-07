/**
 * The OpenAPI page, with a stand-in of Scalar: jsdom doesn't run the vendored build. These test what the page gives
 * Scalar, that it loads Scalar's script only when Scalar isn't there yet, and what it shows when the script fails.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { server } from "@test/server";

import App from "@/App";
import { OPENAPI_JSON_URL, SCALAR_SCRIPT_URL } from "@/lib/docs";
import { loadScalar, SCALAR_CONFIGURATION } from "@/lib/scalar";
import { visitorSession } from "@/mocks/fixtures";
import { sessionHandler } from "@/mocks/handlers";
import { routes } from "@/router";

function mount() {
  server.use(sessionHandler(visitorSession));
  const router = createMemoryRouter(routes, { initialEntries: ["/docs/openapi/"] });
  return render(<App router={router} />);
}

/** Scalar's script element, if the page added one. */
function scalarScript(): HTMLScriptElement | null {
  return document.head.querySelector<HTMLScriptElement>(`script[src="${SCALAR_SCRIPT_URL}"]`);
}

/** How many of Scalar's script elements the page added. */
function scalarScriptCount(): number {
  return document.head.querySelectorAll(`script[src="${SCALAR_SCRIPT_URL}"]`).length;
}

afterEach(() => {
  delete window.Scalar;
  scalarScript()?.remove();
});

describe("the OpenAPI page", () => {
  it("renders the api's document with Scalar, which calls none of Scalar's services", async () => {
    const destroy = vi.fn();
    const createApiReference = vi.fn(() => ({ destroy }));
    window.Scalar = { createApiReference };
    const { unmount } = mount();

    expect(await screen.findByRole("heading", { level: 1, name: "Smarter OpenAPI Contract" })).toBeInTheDocument();
    await waitFor(() => expect(createApiReference).toHaveBeenCalledTimes(1));
    expect(createApiReference).toHaveBeenCalledWith(screen.getByTestId("openapi-reference"), SCALAR_CONFIGURATION);
    expect(SCALAR_CONFIGURATION).toMatchObject({
      url: OPENAPI_JSON_URL,
      proxyUrl: "",
      telemetry: false,
      withDefaultFonts: false,
      showDeveloperTools: "never",
      agent: { disabled: true },
    });
    expect(scalarScript()).toBeNull();
    expect(screen.getByRole("link", { name: "Download openapi.json" })).toHaveAttribute("href", OPENAPI_JSON_URL);

    unmount();
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it("loads Scalar's script, once, and says so when it fails", async () => {
    mount();
    await waitFor(() => expect(scalarScript()).not.toBeNull());
    // a second caller waits for the same script.
    const second = loadScalar();
    expect(scalarScriptCount()).toBe(1);

    scalarScript()?.dispatchEvent(new Event("error"));
    expect(await screen.findByRole("alert")).toHaveTextContent("The OpenAPI reference couldn't be loaded.");
    await expect(second).rejects.toThrow("failed to load");
  });

  it("resolves when the script defines Scalar, and fails when it doesn't", async () => {
    const loading = loadScalar();
    const script = scalarScript();
    const createApiReference = vi.fn();
    window.Scalar = { createApiReference };
    script?.dispatchEvent(new Event("load"));
    await expect(loading).resolves.toEqual({ createApiReference });

    delete window.Scalar;
    script?.remove();
    const failing = loadScalar();
    scalarScript()?.dispatchEvent(new Event("load"));
    await expect(failing).rejects.toThrow("didn't define window.Scalar");
  });
});
