import { act, renderHook } from "@testing-library/react";
import type { KeyboardEvent, PointerEvent } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  CHAT_WIDTH_STORAGE_KEY,
  CONSOLE_VISIBLE_STORAGE_KEY,
  DEFAULT_CHAT_WIDTH,
  KEYBOARD_STEP,
  MAX_CHAT_WIDTH,
  MIN_CHAT_WIDTH,
  clampChatWidth,
  useChatWidth,
  useConsoleVisible,
} from "./layout";

/** A container, 1000px wide, from x = 100. */
function containerRef() {
  const element = document.createElement("div");
  element.getBoundingClientRect = () => ({ left: 100, width: 1000 }) as DOMRect;
  return { current: element };
}

function pointer(clientX: number) {
  const currentTarget = { setPointerCapture: vi.fn(), releasePointerCapture: vi.fn() };
  return { clientX, pointerId: 1, currentTarget, preventDefault: vi.fn() } as unknown as PointerEvent<HTMLElement>;
}

function key(name: string) {
  return { key: name, preventDefault: vi.fn() } as unknown as KeyboardEvent<HTMLElement>;
}

describe("clampChatWidth", () => {
  it("keeps the chat's width between its minimum and maximum", () => {
    expect(clampChatWidth(0)).toBe(MIN_CHAT_WIDTH);
    expect(clampChatWidth(50)).toBe(50);
    expect(clampChatWidth(100)).toBe(MAX_CHAT_WIDTH);
  });
});

describe("useChatWidth", () => {
  afterEach(() => vi.restoreAllMocks());

  it("starts at the default width, which the separator reports", () => {
    const { result } = renderHook(() => useChatWidth(containerRef()));
    expect(result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH);
    expect(result.current.separatorProps).toMatchObject({
      role: "separator",
      "aria-orientation": "vertical",
      "aria-valuenow": Math.round(DEFAULT_CHAT_WIDTH),
      tabIndex: 0,
    });
  });

  it("resizes the chat while the separator is dragged, and remembers its width", () => {
    const { result } = renderHook(() => useChatWidth(containerRef()));
    // a move without a drag does nothing.
    act(() => result.current.separatorProps.onPointerMove(pointer(700)));
    expect(result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH);

    const down = pointer(433);
    act(() => result.current.separatorProps.onPointerDown(down));
    expect(down.currentTarget.setPointerCapture).toHaveBeenCalledWith(1);
    act(() => result.current.separatorProps.onPointerMove(pointer(600)));
    expect(result.current.chatWidth).toBe(50);
    act(() => result.current.separatorProps.onPointerMove(pointer(1100)));
    expect(result.current.chatWidth).toBe(MAX_CHAT_WIDTH);
    act(() => result.current.separatorProps.onPointerUp(pointer(1100)));
    act(() => result.current.separatorProps.onPointerMove(pointer(300)));
    expect(result.current.chatWidth).toBe(MAX_CHAT_WIDTH);
    expect(window.localStorage.getItem(CHAT_WIDTH_STORAGE_KEY)).toBe(String(MAX_CHAT_WIDTH));
  });

  it("ignores a drag over a container without a width", () => {
    const ref = { current: null };
    const { result } = renderHook(() => useChatWidth(ref));
    act(() => result.current.separatorProps.onPointerDown(pointer(0)));
    act(() => result.current.separatorProps.onPointerMove(pointer(500)));
    expect(result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH);
  });

  it("resizes the chat with the keyboard, and restores its default width on double-click", () => {
    const { result } = renderHook(() => useChatWidth(containerRef()));
    act(() => result.current.separatorProps.onKeyDown(key("ArrowRight")));
    expect(result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH + KEYBOARD_STEP);
    act(() => result.current.separatorProps.onKeyDown(key("ArrowLeft")));
    act(() => result.current.separatorProps.onKeyDown(key("ArrowLeft")));
    expect(result.current.chatWidth).toBeCloseTo(DEFAULT_CHAT_WIDTH - KEYBOARD_STEP);
    act(() => result.current.separatorProps.onKeyDown(key("Home")));
    expect(result.current.chatWidth).toBe(MIN_CHAT_WIDTH);
    act(() => result.current.separatorProps.onKeyDown(key("End")));
    expect(result.current.chatWidth).toBe(MAX_CHAT_WIDTH);
    const other = key("a");
    act(() => result.current.separatorProps.onKeyDown(other));
    expect(other.preventDefault).not.toHaveBeenCalled();
    act(() => result.current.separatorProps.onDoubleClick());
    expect(result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH);
  });

  it("starts at the remembered width, and ignores a bad one", () => {
    window.localStorage.setItem(CHAT_WIDTH_STORAGE_KEY, "55");
    expect(renderHook(() => useChatWidth(containerRef())).result.current.chatWidth).toBe(55);
    window.localStorage.setItem(CHAT_WIDTH_STORAGE_KEY, "wide");
    expect(renderHook(() => useChatWidth(containerRef())).result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH);
  });

  it("works without localStorage, e.g. in a private window", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    const { result } = renderHook(() => useChatWidth(containerRef()));
    expect(result.current.chatWidth).toBe(DEFAULT_CHAT_WIDTH);
    act(() => result.current.separatorProps.onKeyDown(key("End")));
    expect(result.current.chatWidth).toBe(MAX_CHAT_WIDTH);
  });
});

describe("useConsoleVisible", () => {
  it("is visible until hidden, and remembers it", () => {
    const { result } = renderHook(() => useConsoleVisible());
    expect(result.current[0]).toBe(true);
    act(() => result.current[1](false));
    expect(result.current[0]).toBe(false);
    expect(window.localStorage.getItem(CONSOLE_VISIBLE_STORAGE_KEY)).toBe("false");
    expect(renderHook(() => useConsoleVisible()).result.current[0]).toBe(false);
  });
});
