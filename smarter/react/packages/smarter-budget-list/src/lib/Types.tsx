/**
 * Central type definitions for the Budget List React application.
 *
 * The objects come from smarter.apps.account.views.budget.listview.BudgetListApiView.
 */
import type { Annotations, Tags, UserProfile } from "@smarter/common";

import type { BudgetPeriod, BudgetUnit } from "@/components/BudgetList/format";

/** A spec.resources entry of a Budget manifest: a kind and name, or a record locator. */
export type BudgetResourceRef = {
  kind?: string;
  name?: string;
  accountNumber?: string;
  recordLocator?: string;
};

/** The budget versus the actual spending of one resource that a budget is attached to. */
export type BudgetResourceStatus = {
  budget: string;
  resourceLocator: string;
  resource: BudgetResourceRef;
  seriesUrl: string;
  isActive: boolean;
  unit: BudgetUnit;
  period: BudgetPeriod;
  startDate: string;
  expiresAt: string | null;
  isExpired: boolean;
  periodStart: string;
  periodEnd: string;
  periodicLimit: number;
  periodicActual: number;
  periodicPercent: number | null;
  absoluteLimit: number;
  absoluteActual: number;
  absolutePercent: number | null;
  isLocked: boolean;
  lockReason: string | null;
};

export type Budget = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;

  unit: BudgetUnit;
  period: BudgetPeriod;
  duration: number;
  periodicLimit: string;
  absoluteLimit: string;
  action: "block" | "warn";
  warningThreshold: number;
  message: string;

  resources: number;
  locked: number;
  resourceStatus: BudgetResourceStatus[];
};

export type BudgetListResponse = {
  user: UserProfile;
  isSuperuser: boolean;
  objects: Budget[];
};
