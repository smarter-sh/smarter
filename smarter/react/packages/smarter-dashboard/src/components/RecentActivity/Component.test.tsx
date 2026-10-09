import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { server } from "@test/server";

import RecentActivity from "@/components/RecentActivity/Component";

const apiUrl = appContext.activityApiUrl;

describe("RecentActivity", () => {
  it.each([
    [true, "No recent activity. Apply, deploy or delete a manifest and it will show here."],
    [false, "Activity journaling is turned off (waffle switch enable_journal)."],
  ])("explains an empty activity list, when journaling is %s", async (journal_enabled, message) => {
    server.use(http.post(apiUrl, () => HttpResponse.json({ journal_enabled, items: [] })));
    render(<RecentActivity sessionContext={sessionContext} apiUrl={apiUrl} />);
    expect(await screen.findByText(message)).toBeInTheDocument();
  });
});
