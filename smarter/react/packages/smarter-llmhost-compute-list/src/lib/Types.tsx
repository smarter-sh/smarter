/**
 * Central type definitions for the LLMHost Compute List React application.
 *
 * An LLMHostCompute is a kind of node, e.g. an AWS g6.2xlarge with one NVIDIA L4 GPU, and the
 * EKS managed node group of those nodes, which Smarter scales as LLMHosts are launched and
 * destroyed.
 *
 * Exports:
 *   - LLMHostCompute: the LLMHostCompute objects, as smarter.apps.llmhost.serializers.LLMHostComputeSerializer serializes them.
 *   - NodeGroupStatus: the node group's status, as the cloud reports it, or "absent".
 *   - Component props interfaces.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Sorting, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// LLMHostCompute Definition
// ----------------------------------------------------------------------------

/**
 * The status of the node group, as the cloud reports it, as of its last reconcile.
 * "absent": Smarter has not created it yet. It does so when an LLMHost first needs one of its nodes.
 */
export type NodeGroupStatus =
  "absent" | "CREATING" | "ACTIVE" | "UPDATING" | "DELETING" | "CREATE_FAILED" | "DELETE_FAILED" | "DEGRADED";

export type LLMHostCompute = {
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  userProfile: UserProfile;
  baseUrl: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  manifestUrl: string;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it
  ready: boolean;
  rfc1034CompliantName: string | null;

  /** The manifest's spec, in camelCase: the source of truth for the node group. */
  spec: Record<string, unknown>;

  // --- The node ---
  /** The cloud's instance type, e.g. "g6.2xlarge". */
  instanceType: string;
  /** vCPUs. */
  cpu: number;
  /** GiB. */
  memoryGb: number;
  /** e.g. "L4". Empty for a CPU node. */
  gpuType: string;
  gpuCount: number;
  /** The memory of one GPU, in GB. */
  gpuMemoryGb: number;
  /** The most nodes that Smarter adds to the node group. */
  maxNodes: number;
  /** The cost per hour of one node, a decimal string, e.g. "0.9776". */
  pricePerHour: string | null;

  // --- The node group, as of its last reconcile ---
  /** The cloud's name of the node group, e.g. "smarter-alpha-12-gpu-l4-1x". */
  nodegroupName: string;
  nodegroupStatus: NodeGroupStatus;
  desiredNodes: number;
  readyNodes: number;
  statusMessage: string;
  lastReconciledAt: string | null;
  /** The LLMHosts that run on it. */
  llmhostCount: number;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface LLMHostComputeCardViewProps {
  sessionContext: SessionContext;
  objects: LLMHostCompute[];
  onRequery: () => void;
}

export interface LLMHostComputeListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: LLMHostCompute[];
  onRequery: () => void;
  sorting?: Sorting;
}
