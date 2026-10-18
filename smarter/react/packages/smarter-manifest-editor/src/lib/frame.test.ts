import { afterEach, describe, expect, it, vi } from "vitest";

import { MANIFEST_SAVED_MESSAGE, framingWindow, notifySaved } from "@/lib/frame";
import { parseManifest } from "@/lib/manifest";
import { appProps } from "@/mocks/fixtures";

describe("frame", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("has no framing page at the top of the window", () => {
    expect(framingWindow()).toBeNull();
    // and nothing to tell.
    notifySaved(parseManifest(appProps.initialManifest));
  });

  it("finds the framing page of its own origin, and tells it that the manifest was saved", () => {
    const parent = { location: { href: "http://localhost:9357/workbench/" }, postMessage: vi.fn() };
    vi.stubGlobal("parent", parent);
    expect(framingWindow()).toBe(parent);

    notifySaved(parseManifest(appProps.initialManifest));
    expect(parent.postMessage).toHaveBeenCalledWith(
      { type: MANIFEST_SAVED_MESSAGE, kind: "Secret", name: "example_secret" },
      window.location.origin,
    );
  });

  it("ignores a framing page of another origin", () => {
    const parent = {
      get location(): Location {
        throw new DOMException("Blocked a frame with origin", "SecurityError");
      },
      postMessage: vi.fn(),
    };
    vi.stubGlobal("parent", parent);
    expect(framingWindow()).toBeNull();
    notifySaved(parseManifest(appProps.initialManifest));
    expect(parent.postMessage).not.toHaveBeenCalled();
  });
});
