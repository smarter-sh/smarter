import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { chatStyles } from "@/mocks/fixtures";
import {
  GOOGLE_FONT_LINK_ID,
  fontFamily,
  googleFontUrl,
  safeCssValue,
  safeImageUrl,
  styleVariables,
  useGoogleFont,
} from "@/lib/styles";

describe("safeCssValue", () => {
  it("accepts plain css values", () => {
    for (const value of ["#ff5733", "rgba(0, 0, 0, 0.5)", "tomato", "16px", '"Fredoka", sans-serif']) {
      expect(safeCssValue(` ${value} `)).toBe(value);
    }
  });

  it("rejects values that could do more than set a value", () => {
    for (const value of [
      "red; background: blue",
      "url(https://evil.example.com/x.png)",
      "URL (x)",
      "var(--x)",
      "expression(alert(1))",
      "image-set(x)",
      "a{b}",
      "red !important",
      "\\72 ed",
      "@import",
      "",
    ]) {
      expect(safeCssValue(value)).toBeNull();
    }
    expect(safeCssValue(null)).toBeNull();
    expect(safeCssValue(undefined)).toBeNull();
  });
});

describe("safeImageUrl", () => {
  it("accepts https urls", () => {
    expect(safeImageUrl("https://cdn.smarter.sh/a.png")).toBe("https://cdn.smarter.sh/a.png");
  });

  it("rejects other urls, and urls that could end css' url()", () => {
    for (const url of [
      "javascript:alert(1)",
      "data:image/png;base64,AA",
      'https://x.com/a.png")',
      "https://x.com/a b",
    ]) {
      expect(safeImageUrl(url)).toBeNull();
    }
    expect(safeImageUrl(null)).toBeNull();
  });
});

describe("googleFontUrl and fontFamily", () => {
  it("builds the font's Google Fonts stylesheet url", () => {
    expect(googleFontUrl("Space Grotesk")).toBe(
      "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap",
    );
    expect(googleFontUrl("Nunito&display=block")).toBeNull();
    expect(googleFontUrl(undefined)).toBeNull();
  });

  it("prefers fontFamily, then the Google font, then chatscope's", () => {
    expect(fontFamily({ font_family: "Georgia, serif", google_font: "Nunito" })).toBe("Georgia, serif");
    expect(fontFamily({ google_font: "Nunito" })).toBe('"Nunito", system-ui, sans-serif');
    expect(fontFamily({})).toBeNull();
    expect(fontFamily(null)).toBeNull();
  });
});

describe("styleVariables", () => {
  it("has no variables without styles", () => {
    expect(styleVariables(null)).toEqual({});
    expect(styleVariables({})).toEqual({});
  });

  it("sets a variable for each setting", () => {
    const variables = styleVariables(chatStyles) as Record<string, string>;
    expect(variables["--smarter-chat-font-family"]).toBe('"Nunito", system-ui, sans-serif');
    expect(variables["--smarter-chat-font-size"]).toBe("15px");
    expect(variables["--smarter-chat-border-radius"]).toBe("16px");
    expect(variables["--smarter-chat-header-bg"]).toBe("#14213d");
    expect(variables["--smarter-chat-header-info-color"]).toBe("#fca311");
    expect(variables["--smarter-chat-incoming-bg"]).toBe("#e5e5e5");
    expect(variables["--smarter-chat-incoming-link-color"]).toBe("#0b57d0");
    expect(variables["--smarter-chat-incoming-link-filter"]).toBe("none");
    expect(variables["--smarter-chat-outgoing-link-filter"]).toBeUndefined();
    expect(variables["--smarter-chat-input-editor-bg"]).toBe("#f1f1f1");
    expect(variables["--smarter-chat-input-placeholder-color"]).toBe("#6c757d");
    expect(variables["--smarter-chat-button-color"]).toBe("#fca311");
    expect(variables["--smarter-chat-typing-color"]).toBe("#fca311");
  });

  it("tints the background image with the message list's color", () => {
    const variables = styleVariables(chatStyles) as Record<string, string>;
    expect(variables["--smarter-chat-background-image"]).toBe(
      'linear-gradient(rgba(255, 255, 255, 0.85), rgba(255, 255, 255, 0.85)), url("https://cdn.smarter.sh/images/stackademy-background.png")',
    );
    expect(variables["--smarter-chat-message-list-bg"]).toBe("transparent");
    expect(variables["--smarter-chat-background-size"]).toBe("cover");
    expect(variables["--smarter-chat-background-repeat"]).toBe("no-repeat");
  });

  it("tiles a background image at its own size, untinted without a message list color", () => {
    const variables = styleVariables({
      app_background_image_url: "https://cdn.smarter.sh/tile.png",
      app_background_image_size: "auto",
    }) as Record<string, string>;
    expect(variables["--smarter-chat-background-image"]).toBe(
      'linear-gradient(transparent, transparent), url("https://cdn.smarter.sh/tile.png")',
    );
    expect(variables["--smarter-chat-background-repeat"]).toBe("repeat");
  });

  it("makes the chat container transparent over the main container's color", () => {
    const variables = styleVariables({ main_container: { background_color: "#000" } }) as Record<string, string>;
    expect(variables["--smarter-chat-main-container-bg"]).toBe("#000");
    expect(variables["--smarter-chat-chat-container-bg"]).toBe("transparent");
  });

  it("ignores invalid values, and sections that aren't objects", () => {
    const variables = styleVariables({
      font_size: "1px; color: red",
      app_background_image_url: "javascript:alert(1)",
      conversation_header: { background_color: "url(https://evil.example.com)" },
      buttons: "red" as never,
    });
    expect(variables).toEqual({});
  });
});

/* eslint-disable testing-library/no-node-access -- the font's stylesheet is a link in the page's head. */
describe("useGoogleFont", () => {
  afterEach(() => document.getElementById(GOOGLE_FONT_LINK_ID)?.remove());

  it("adds the font's stylesheet to the page once, and changes it with the font", () => {
    const { rerender } = renderHook(({ name }) => useGoogleFont(name), { initialProps: { name: "Nunito" } });
    const link = document.getElementById(GOOGLE_FONT_LINK_ID) as HTMLLinkElement;
    expect(link.rel).toBe("stylesheet");
    expect(link.href).toContain("family=Nunito");
    rerender({ name: "Fredoka" });
    expect(document.querySelectorAll(`#${GOOGLE_FONT_LINK_ID}`)).toHaveLength(1);
    expect(link.href).toContain("family=Fredoka");
  });

  it("adds nothing without a valid font", () => {
    renderHook(() => useGoogleFont("bad&name"));
    renderHook(() => useGoogleFont(null));
    expect(document.getElementById(GOOGLE_FONT_LINK_ID)).toBeNull();
  });
});
/* eslint-enable testing-library/no-node-access */
