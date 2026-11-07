/**
 * The resource lists that have moved into the console. Each is a package's list component (@smarter/<kind>-list)
 * at the path that Django served it at, without the trailing slash, with its list api in the console's web api. The
 * router gives each a route, whose component loads in a chunk of its own; the sidebar opens it in place.
 */
import type { SessionContext } from "@smarter/common";
import type { OnboardingContext } from "@smarter/onboarding";
import type { ComponentType } from "react";

import type { ConsoleSession } from "@/contract.gen";

/**
 * What the console gives a list component: the session context of its requests, and the onboarding hints' state,
 * which the LLMClient list reads for its weather hint and the others ignore.
 */
export interface ListProps {
  sessionContext: SessionContext;
  onboarding?: OnboardingContext | null;
}

/** A list component: what each package's src/index.ts exports. */
export type ListComponent = ComponentType<ListProps>;

export interface ListPage {
  /** The console's route, e.g. /guardrail: Django's /guardrail/. */
  path: string;
  /** The list api, /api/web/<app>/listview/, whose owned/, shared/ and all/ the list calls. */
  apiUrl: string;
  /** Loads the package's list component. */
  load: () => Promise<ListComponent>;
  /**
   * Whether the session may see the list, as the backend decides it for its page: a feature that the platform has
   * turned off, or a list for superusers only. Without it, any signed-in user may. Otherwise the page is not found.
   */
  visible?: (session: ConsoleSession) => boolean;
}

export const LIST_PAGES: ListPage[] = [
  {
    path: "/workbench",
    apiUrl: "/api/web/prompt/listview/",
    load: async () => (await import("@smarter/llmclient-list")).LLMClientList,
  },
  {
    path: "/provider",
    apiUrl: "/api/web/provider/listview/",
    load: async () => (await import("@smarter/provider-list")).ProviderList,
  },
  {
    path: "/proxy",
    apiUrl: "/api/web/proxy/listview/",
    load: async () => (await import("@smarter/proxy-list")).ProxyList,
    visible: (session) => session.flags.proxy,
  },
  {
    path: "/llmhost",
    apiUrl: "/api/web/llmhost/listview/",
    load: async () => (await import("@smarter/llmhost-list")).LLMHostList,
  },
  {
    path: "/llmhost/compute",
    apiUrl: "/api/web/llmhost/compute/listview/",
    load: async () => (await import("@smarter/llmhost-compute-list")).LLMHostComputeList,
  },
  {
    path: "/orchestrator",
    apiUrl: "/api/web/orchestrator/listview/",
    load: async () => (await import("@smarter/orchestrator-list")).OrchestratorList,
  },
  {
    path: "/authtoken",
    apiUrl: "/api/web/authtoken/listview/",
    load: async () => (await import("@smarter/authtoken-list")).AuthTokenList,
  },
  {
    path: "/llmclient/custom-domains",
    apiUrl: "/api/web/llmclient/custom-domains/listview/",
    load: async () => (await import("@smarter/custom-domain-list")).CustomDomainList,
  },
  {
    path: "/llm-tools",
    apiUrl: "/api/web/llmtool/listview/",
    load: async () => (await import("@smarter/llmtool-list")).LLMToolList,
  },
  {
    path: "/mcpclient",
    apiUrl: "/api/web/mcpclient/listview/",
    load: async () => (await import("@smarter/mcpclient-list")).MCPClientList,
  },
  {
    path: "/connection",
    apiUrl: "/api/web/connection/listview/",
    load: async () => (await import("@smarter/connection-list")).ConnectionList,
  },
  {
    path: "/vectorsearch",
    apiUrl: "/api/web/vectorsearch/listview/",
    load: async () => (await import("@smarter/vectorsearch-list")).VectorsearchList,
  },
  {
    path: "/vectorstore",
    apiUrl: "/api/web/vectorstore/listview/",
    load: async () => (await import("@smarter/vectorstore-list")).VectorstoreList,
    visible: (session) => session.flags.vectorstore,
  },
  {
    path: "/budget",
    apiUrl: "/api/web/account/budget/listview/",
    load: async () => (await import("@smarter/budget-list")).BudgetList,
  },
  {
    path: "/guardrail",
    apiUrl: "/api/web/guardrail/listview/",
    load: async () => (await import("@smarter/guardrail-list")).GuardrailList,
  },
  {
    path: "/secret",
    apiUrl: "/api/web/secret/listview/",
    load: async () => (await import("@smarter/secret-list")).SecretList,
  },
  {
    path: "/infrastructure",
    apiUrl: "/api/web/infrastructure/listview/",
    load: async () => (await import("@smarter/infrastructure-resource-list")).InfrastructureResourceList,
    visible: (session) => session.user?.isSuperuser ?? false,
  },
];
