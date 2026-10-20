import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { useTargetBox } from "@/lib/useTargetBox";
import { addTarget, removeTargets, stubBox } from "@/mocks/targets";

describe("useTargetBox", () => {
  afterEach(removeTargets);

  it("follows the element's box, and is null while it is off screen", async () => {
    const element = addTarget("<a href='/'>Link</a>", { top: 10, left: 20, width: 100, height: 30 });
    const { result } = renderHook(() => useTargetBox(element));
    expect(result.current).toEqual({ top: 10, left: 20, width: 100, height: 30 });
    stubBox(element, { top: 50, left: 20, width: 100, height: 30 });
    await waitFor(() => expect(result.current?.top).toBe(50));
    stubBox(element, { top: 0, left: 0, width: 0, height: 0 });
    await waitFor(() => expect(result.current).toBeNull());
  });

  it("is null without an element", () => {
    const { result } = renderHook(() => useTargetBox(null));
    expect(result.current).toBeNull();
  });
});
