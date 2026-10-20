import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "@test/server";
import { useOnboarding, type OnboardingContext } from "@smarter/onboarding";

import WeatherHint from "@/components/WeatherHint/Component";
import { weatherTargetAttribute } from "@/components/WeatherHint/const";

const context: OnboardingContext = {
  enabled: true,
  apiUrl: "/dashboard/api/onboarding/seen/",
  seen: [],
  csrfCookieName: "csrftoken",
  cookieDomain: "localhost",
};

function Hint({ onboarding }: { onboarding: OnboardingContext }) {
  return <WeatherHint onboarding={useOnboarding(onboarding)} />;
}

const links: HTMLAnchorElement[] = [];

/** The Get Weather LLMClient's name, as the list renders it, laid out on the page. */
function addWeatherLink() {
  const link = document.createElement("a");
  link.href = "/workbench/llm-clients/3f2a9c/prompt/";
  link.textContent = "weather";
  link.setAttribute("data-smarter-onboarding", "llmclient-weather");
  document.body.append(link);
  links.push(link);
  vi.spyOn(link, "getBoundingClientRect").mockReturnValue({
    top: 300,
    left: 100,
    width: 80,
    height: 20,
    x: 100,
    y: 300,
    right: 180,
    bottom: 320,
    toJSON: () => ({}),
  } as DOMRect);
  return link;
}

describe("WeatherHint", () => {
  let posted: unknown[];
  beforeEach(() => {
    posted = [];
    server.use(
      http.post(context.apiUrl, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ seen: [] });
      }),
    );
  });
  afterEach(() => {
    for (const link of links.splice(0)) link.remove();
  });

  it("spotlights the Get Weather LLMClient's name, and records the click on it", async () => {
    const link = addWeatherLink();
    render(<Hint onboarding={context} />);
    const note = await screen.findByRole("dialog", { name: "Start with the weather LLMClient" });
    expect(note).toHaveAccessibleDescription(/Click its name to chat with it/);
    fireEvent.click(link);
    await waitFor(() => expect(posted).toEqual([{ hint: "llmclient_weather", outcome: "clicked" }]));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("shows nothing once seen", () => {
    addWeatherLink();
    render(<Hint onboarding={{ ...context, seen: ["llmclient_weather"] }} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("weatherTargetAttribute", () => {
  it("marks only the Get Weather LLMClient", () => {
    expect(weatherTargetAttribute("weather")).toEqual({ "data-smarter-onboarding": "llmclient-weather" });
    expect(weatherTargetAttribute("stackademy")).toEqual({});
  });
});
