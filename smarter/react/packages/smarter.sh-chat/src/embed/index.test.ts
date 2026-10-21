/* eslint-disable testing-library/no-node-access -- the script adds its elements to the page itself. */
import { act } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { projectVersion } from "@/const";
import { API_URL } from "@/mocks/fixtures";
import { chatHandlers } from "@/mocks/handlers";
import { server } from "@test/server";
import type { SmarterChatElement } from "./element";

afterEach(async () => {
  await act(async () => {
    document.body.innerHTML = "";
  });
  delete window.SmarterChatConfig;
});

describe("the embed script", () => {
  it("defines <smarter-chat>, adds window.SmarterChatConfig's launcher, and sets window.SmarterChat", async () => {
    server.use(...chatHandlers);
    window.SmarterChatConfig = { chatbot: API_URL, label: "Help" };
    await act(async () => {
      await import("./index");
    });
    expect(customElements.get("smarter-chat")).toBeDefined();
    const api = window.SmarterChat!;
    expect(api.version).toBe(projectVersion);
    const launcher = document.querySelector<SmarterChatElement>("smarter-chat")!;
    expect(launcher).toHaveAttribute("mode", "launcher");

    await act(async () => api.open());
    expect(launcher.isOpen).toBe(true);
    await act(async () => api.close("https://elsewhere.example.com/"));
    expect(launcher.isOpen).toBe(true);
    await act(async () => api.toggle(API_URL));
    expect(launcher.isOpen).toBe(false);
    await act(async () => api.close());
    expect(launcher.isOpen).toBe(false);

    document.body.innerHTML = '<div id="inline"></div>';
    let inline: HTMLElement | null = null;
    await act(async () => {
      inline = api.mount({ chatbot: API_URL, target: "#inline" });
    });
    expect(inline).toHaveAttribute("mode", "inline");
    // inline chats aren't launchers, and are left alone.
    const open = vi.spyOn(inline! as SmarterChatElement, "open");
    await act(async () => api.open());
    expect(open).not.toHaveBeenCalled();
  });
});
