import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { appContext, quickActions } from "@/mocks/fixtures";
import { server } from "@test/server";

import QuickActions from "@/components/QuickActions/Component";

const apiUrl = appContext.quickActionsApiUrl;

describe("QuickActions", () => {
  it("links each action, with its description as its tooltip", async () => {
    server.use(http.post(apiUrl, () => HttpResponse.json(quickActions)));
    render(<QuickActions sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    const guardrails = await screen.findByRole("link", { name: "Guardrails" });
    expect(guardrails).toHaveAttribute("href", "/guardrail/");
    expect(guardrails).toHaveAttribute("title", "Screen prompts and responses");
    expect(screen.getAllByRole("link")).toHaveLength(quickActions.length);
  });

  it("opens an external link in a new tab", async () => {
    server.use(http.post(apiUrl, () => HttpResponse.json(quickActions)));
    render(<QuickActions sessionContext={appContext.sessionContext} apiUrl={apiUrl} />);
    expect(await screen.findByRole("link", { name: "Documentation" })).toHaveAttribute("target", "_blank");
    expect(screen.getByRole("link", { name: "Guardrails" })).not.toHaveAttribute("target");
  });
});
