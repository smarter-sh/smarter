/**
 * Example data for this package's stories and tests: what the Django dashboard api returns.
 * See smarter.apps.dashboard.views.views.api.
 */
import type { SessionContext } from "@smarter/common";

import type { BudgetSeries, BudgetStatus } from "@/components/BudgetVsActual/types";
import type { TokenUsageInterface } from "@/components/TokenUsage/types";
import type { AppContextInterface } from "@/main";

export const sessionContext: SessionContext = {
  ApiUrl: "/dashboard/api/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/dashboard",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export const appContext: AppContextInterface = {
  sessionContext,
  myResourcesApiUrl: "/dashboard/api/my-resources/",
  serviceHealthApiUrl: "/dashboard/api/service-health/",
  chargesApiUrl: "/dashboard/api/charges/",
  budgetsApiUrl: "/dashboard/api/budgets/",
  activityApiUrl: "/dashboard/api/activity/",
  gettingStartedApiUrl: "/dashboard/api/getting-started/",
  quickActionsApiUrl: "/dashboard/api/quick-actions/",
};

export const myResources = {
  pending_deployments: 2,
  llmclients_qty: 5,
  llmclients_url: "/workbench/",
  plugins_qty: 7,
  plugins_url: "/plugin/",
  connections_qty: 3,
  connections_url: "/connection/",
  providers_qty: 4,
  providers_url: "/provider/",
};

export const serviceHealth = {
  linux_distribution: "Debian GNU/Linux 13",
  smarter_version: "0.18.0",
  django_version: "6.0.8",
  python_version: "3.14.0",
  pydantic_version: "2.13.5",
  drf_version: "3.16.1",
  health_checks: [
    { name: "Database", healthy: true },
    { name: "Redis", healthy: true },
    { name: "Celery", healthy: true },
    { name: "Kubernetes", healthy: false },
  ],
  health_score: 75,
};

export const quickActions = [
  { name: "New LLMClient", description: "Apply an LLMClient manifest", icon: "ki-rocket", url: "/workbench/" },
  { name: "Documentation", description: "docs.smarter.sh", icon: "ki-book", url: "https://docs.smarter.sh/" },
];

export const gettingStarted = {
  steps: [
    { name: "Create an API key", description: "For the smarter CLI.", done: true, url: "/authtoken/" },
    { name: "Apply a manifest", description: "Create your first LLMClient.", done: false, url: "/workbench/" },
    { name: "Deploy it", description: "Serve it on its own url.", done: false, url: "/workbench/" },
  ],
};

export const activity = {
  journal_enabled: true,
  items: [
    { created_at: "2026-06-15T12:00:00Z", thing: "LLMClient", command: "apply", status_code: 200, message: null },
    { created_at: "2026-06-15T11:00:00Z", thing: "Plugin", command: "delete", status_code: 404, message: "Not found" },
  ],
};

export const tokenUsage: TokenUsageInterface[] = ["10:00", "11:00", "12:00"].map((time, i) => ({
  timestamp: `2026-06-15T${time}:00Z`,
  requestTokens: [1200, 2400, 1800][i],
  completionTokens: [800, 1600, 900][i],
  budgetTokens: 10000,
  totalTokens: [2000, 4000, 2700][i],
  remainingTokens: [8000, 4000, 1300][i],
  utilization: [20, 60, 87][i],
}));

export function makeBudgetStatus(overrides: Partial<BudgetStatus> = {}): BudgetStatus {
  return {
    budget: "monthly_llm_budget",
    resource_locator: "llmclient:example",
    is_active: true,
    unit: "cost",
    period: "month",
    action: "block",
    start_date: "2026-01-01T00:00:00Z",
    expires_at: null,
    is_expired: false,
    period_start: "2026-06-01T00:00:00Z",
    period_end: "2026-07-01T00:00:00Z",
    periodic_limit: 100,
    periodic_actual: 42.5,
    periodic_percent: 43,
    absolute_limit: 0,
    absolute_actual: 312.75,
    absolute_percent: null,
    is_locked: false,
    lock_reason: null,
    ...overrides,
  };
}

export const budgets: BudgetStatus[] = [
  makeBudgetStatus(),
  makeBudgetStatus({
    budget: "daily_token_budget",
    resource_locator: "proxy:openai",
    unit: "tokens",
    period: "day",
    periodic_limit: 100000,
    periodic_actual: 100250,
    periodic_percent: 100,
    is_locked: true,
    lock_reason: "The daily token budget is exhausted.",
  }),
];

export const budgetSeries: BudgetSeries[] = budgets.map((status) => ({
  status,
  series: ["2026-04-01", "2026-05-01", "2026-06-01"].map((start, i) => ({
    period_start: `${start}T00:00:00Z`,
    period_end: `${start}T00:00:00Z`,
    budget: status.periodic_limit,
    actual: [0.64, 0.97, 0.42][i] * status.periodic_limit,
    total_tokens: 0,
    total_cost: 0,
  })),
}));
