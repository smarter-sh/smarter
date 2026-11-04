import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import App from "@/App";
import { browserTimeZone } from "@/lib/api";
import { appContext, diwali, drawnByAi, quietDay } from "@/mocks/fixtures";
import { server } from "@test/server";

/** Answers the doodle api with a response, and records the time zones that it is asked for. */
function useDoodleApi(body: object, status = 200) {
  const timeZones = vi.fn();
  server.use(
    http.get(appContext.apiUrl, ({ request }) => {
      timeZones(new URL(request.url).searchParams.get("tz"));
      return HttpResponse.json(body, { status });
    }),
  );
  return timeZones;
}

describe("App", () => {
  it("shows the base scene, the logo, the name and the description at once", () => {
    useDoodleApi(diwali);
    render(<App appContext={appContext} timeZone="Asia/Kolkata" />);
    expect(screen.getByRole("heading", { name: "The Smarter Project" })).toBeInTheDocument();
    expect(screen.getByAltText("Logo")).toHaveAttribute("src", appContext.logoUrl);
    expect(screen.getByRole("link", { name: "Learn more" })).toHaveAttribute("href", appContext.projectUrl);
    expect(screen.getByTestId("smarter-doodle-image")).toHaveAttribute("src", appContext.baseImageUrl);
  });

  it("shows the doodle of the day of the visitor's time zone, with its caption", async () => {
    const timeZones = useDoodleApi({ ...diwali, imageUrl: "/api/v1/doodles/artwork/abc.svg" });
    render(<App appContext={appContext} timeZone="Asia/Kolkata" />);
    const image = await screen.findByAltText(diwali.altText);
    expect(image).toHaveAttribute("src", "/api/v1/doodles/artwork/abc.svg");
    expect(timeZones).toHaveBeenCalledWith("Asia/Kolkata");
    const caption = screen.getByRole("link", { name: "Happy Diwali!" });
    expect(caption).toHaveAttribute("href", diwali.linkUrl);
    expect(screen.getByTestId("smarter-doodle-figure")).toHaveAttribute("data-theme", "diwali");
    fireEvent.load(image);
    expect(image).toHaveClass("smarter-doodle-image-loaded");
  });

  it("credits the Smarter AI applications that drew the doodle, in place of the description", async () => {
    useDoodleApi(drawnByAi);
    render(<App appContext={appContext} timeZone="America/Mexico_City" />);
    const credit = await screen.findByTestId("smarter-doodle-ai-credit");
    expect(credit).toHaveTextContent("Drawn by a Smarter AI application.");
    expect(screen.getByRole("link", { name: "Learn how" })).toHaveAttribute("href", drawnByAi.learnHowUrl);
    expect(screen.queryByText(appContext.productDescription, { exact: false })).not.toBeInTheDocument();
  });

  it("credits the Smarter AI application that chose the doodle", async () => {
    useDoodleApi({ ...diwali, aiCredit: "chosen" });
    render(<App appContext={appContext} timeZone="Asia/Kolkata" />);
    expect(await screen.findByTestId("smarter-doodle-ai-credit")).toHaveTextContent(
      "Chosen by a Smarter AI application.",
    );
  });

  it("shows a caption without a link as text", async () => {
    useDoodleApi({ ...diwali, linkUrl: "" });
    render(<App appContext={appContext} timeZone="Asia/Kolkata" />);
    expect(await screen.findByText("Happy Diwali!")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Happy Diwali!" })).not.toBeInTheDocument();
  });

  it("shows no caption on a quiet day", async () => {
    useDoodleApi(quietDay);
    render(<App appContext={appContext} timeZone="UTC" />);
    await screen.findByAltText(quietDay.altText);
    expect(screen.queryByTestId("smarter-doodle-caption")).not.toBeInTheDocument();
  });

  it("asks for the global doodle when the browser has no time zone", async () => {
    const timeZones = useDoodleApi(quietDay);
    render(<App appContext={appContext} timeZone="" />);
    await waitFor(() => expect(timeZones).toHaveBeenCalledWith(null));
  });

  it("keeps the base scene when the api fails", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const timeZones = useDoodleApi({}, 500);
    render(<App appContext={appContext} timeZone="UTC" />);
    await waitFor(() => expect(timeZones).toHaveBeenCalled());
    await waitFor(() => expect(warn).toHaveBeenCalled());
    expect(screen.getByTestId("smarter-doodle-image")).toHaveAttribute("src", appContext.baseImageUrl);
    warn.mockRestore();
  });
});

describe("browserTimeZone", () => {
  it("is the browser's time zone", () => {
    expect(typeof browserTimeZone()).toBe("string");
  });

  it("is empty when the browser can't say", () => {
    const spy = vi.spyOn(Intl, "DateTimeFormat").mockImplementation(() => {
      throw new Error("no Intl");
    });
    expect(browserTimeZone()).toBe("");
    spy.mockRestore();
  });
});
