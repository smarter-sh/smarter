import { describe, expect, it } from "vitest";

import { ANSI_PALETTE, ansiCss, applySgr, parseAnsi, stripAnsi } from "./ansi";

const ESC = "\u001b";

describe("parseAnsi", () => {
  it("splits text into segments with the colors and emphasis of its SGR codes", () => {
    expect(parseAnsi(`INFO ${ESC}[1;34mlogger${ESC}[0m done`)).toEqual([
      { text: "INFO ", style: {} },
      { text: "logger", style: { bold: true, color: ANSI_PALETTE[4] } },
      { text: " done", style: {} },
    ]);
  });

  it("supports bright, background, 256 and true colors", () => {
    expect(parseAnsi(`${ESC}[92ma`)[0].style).toEqual({ color: ANSI_PALETTE[10] });
    expect(parseAnsi(`${ESC}[41;103ma`)[0].style).toEqual({ backgroundColor: ANSI_PALETTE[11] });
    expect(parseAnsi(`${ESC}[38;5;1ma`)[0].style).toEqual({ color: ANSI_PALETTE[1] });
    expect(parseAnsi(`${ESC}[38;5;16ma`)[0].style).toEqual({ color: "rgb(0, 0, 0)" });
    expect(parseAnsi(`${ESC}[38;5;231ma`)[0].style).toEqual({ color: "rgb(255, 255, 255)" });
    expect(parseAnsi(`${ESC}[48;5;232ma`)[0].style).toEqual({ backgroundColor: "rgb(8, 8, 8)" });
    expect(parseAnsi(`${ESC}[38;2;1;2;3ma`)[0].style).toEqual({ color: "rgb(1, 2, 3)" });
  });

  it("ignores invalid extended colors", () => {
    expect(parseAnsi(`${ESC}[38;5;999ma`)[0].style).toEqual({ color: undefined });
    expect(parseAnsi(`${ESC}[38;2;1;2;999ma`)[0].style).toEqual({ color: undefined });
    expect(parseAnsi(`${ESC}[38;9ma`)[0].style).toEqual({ color: undefined });
  });

  it("resets, with an empty code or with 0, and removes other escape sequences", () => {
    expect(parseAnsi(`${ESC}[31ma${ESC}[mb`)).toEqual([
      { text: "a", style: { color: ANSI_PALETTE[1] } },
      { text: "b", style: {} },
    ]);
    expect(parseAnsi(`${ESC}[31;ma`)[0].style).toEqual({});
    expect(parseAnsi(`${ESC}[2Ka${ESC}[?25lb`)).toEqual([
      { text: "a", style: {} },
      { text: "b", style: {} },
    ]);
    expect(parseAnsi("")).toEqual([]);
  });
});

describe("applySgr", () => {
  it("turns emphasis and colors on and off", () => {
    const on = applySgr({}, [1, 2, 3, 4, 33, 44]);
    expect(on).toEqual({
      bold: true,
      dim: true,
      italic: true,
      underline: true,
      color: ANSI_PALETTE[3],
      backgroundColor: ANSI_PALETTE[4],
    });
    expect(applySgr(on, [22, 23, 24, 39, 49])).toEqual({
      bold: undefined,
      dim: undefined,
      italic: undefined,
      underline: undefined,
      color: undefined,
      backgroundColor: undefined,
    });
  });
});

describe("ansiCss", () => {
  it("is the css of a style", () => {
    expect(ansiCss({})).toEqual({});
    expect(
      ansiCss({ color: "red", backgroundColor: "blue", bold: true, dim: true, italic: true, underline: true }),
    ).toEqual({
      color: "red",
      backgroundColor: "blue",
      fontWeight: "bold",
      opacity: 0.7,
      fontStyle: "italic",
      textDecoration: "underline",
    });
  });
});

describe("stripAnsi", () => {
  it("removes the escape sequences", () => {
    expect(stripAnsi(`${ESC}[1;31mERROR${ESC}[0m`)).toBe("ERROR");
  });
});
