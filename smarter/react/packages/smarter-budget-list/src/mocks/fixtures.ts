/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.account.views.budget.listview.BudgetListApiView.
 */
import type { SessionContext } from "@smarter/common";

import type { BudgetSeriesRow } from "@/components/BudgetList/format";
import type { Budget, BudgetListResponse, BudgetResourceStatus } from "@/lib/Types";

export const API_URL = "/budget/react-integration/api/listview/";
export const SERIES_URL = "/dashboard/api/budgets/series/";

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/budget-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export function makeResourceStatus(overrides: Partial<BudgetResourceStatus> = {}): BudgetResourceStatus {
  return {
    budget: "monthly_llm_budget",
    resourceLocator: "llmclient:example",
    resource: { kind: "LLMClient", name: "example", accountNumber: "3141-5926-5359" },
    seriesUrl: SERIES_URL,
    isActive: true,
    unit: "cost",
    period: "month",
    startDate: "2026-01-01T00:00:00Z",
    expiresAt: null,
    isExpired: false,
    periodStart: "2026-06-01T00:00:00Z",
    periodEnd: "2026-07-01T00:00:00Z",
    periodicLimit: 100,
    periodicActual: 42.5,
    periodicPercent: 43,
    absoluteLimit: 0,
    absoluteActual: 312.75,
    absolutePercent: null,
    isLocked: false,
    lockReason: null,
    ...overrides,
  };
}

export function makeBudget(id: number, overrides: Partial<Budget> = {}): Budget {
  return {
    id,
    hashedId: `hashed${id}`,
    createdAt: "2026-01-01T12:00:00Z",
    updatedAt: "2026-06-15T12:00:00Z",
    name: `example_budget_${id}`,
    description: `An example budget, number ${id}.`,
    version: "1.0.0",
    tags: ["example"],
    annotations: [],
    manifestUrl: `/budget/budgets/hashed${id}/`,
    unit: "cost",
    period: "month",
    duration: 0,
    periodicLimit: "100.00",
    absoluteLimit: "0",
    action: "block",
    warningThreshold: 80,
    message: "This resource has reached its monthly budget.",
    resources: 1,
    locked: 0,
    resourceStatus: [makeResourceStatus()],
    ...overrides,
  };
}

export const budgets: Budget[] = [
  makeBudget(1, { name: "monthly_llm_budget", description: "A monthly limit on LLM spending." }),
  makeBudget(2, {
    name: "daily_token_budget",
    description: "A daily limit on tokens, which one resource has reached.",
    unit: "tokens",
    period: "day",
    periodicLimit: "100000",
    action: "warn",
    resources: 2,
    locked: 1,
    resourceStatus: [
      makeResourceStatus({
        budget: "daily_token_budget",
        resourceLocator: "proxy:openai",
        resource: { kind: "Proxy", name: "openai" },
        unit: "tokens",
        period: "day",
        periodicLimit: 100000,
        periodicActual: 100250,
        periodicPercent: 100,
        isLocked: true,
        lockReason: "The daily token budget is exhausted.",
      }),
      makeResourceStatus({ budget: "daily_token_budget", unit: "tokens", period: "day", periodicLimit: 100000 }),
    ],
  }),
];

export const listResponse: BudgetListResponse = {
  user: { user: { username: "admin", email: "admin@example.com" }, account: { accountNumber: "3141-5926-5359" } },
  isSuperuser: true,
  objects: budgets,
};

export const series: BudgetSeriesRow[] = ["2026-04-01", "2026-05-01", "2026-06-01"].map((start, i) => ({
  period_start: `${start}T00:00:00Z`,
  period_end: `${start}T00:00:00Z`,
  budget: 100,
  actual: [64.1, 97.3, 42.5][i],
  total_tokens: [64100, 97300, 42500][i],
  total_cost: [64.1, 97.3, 42.5][i],
}));
