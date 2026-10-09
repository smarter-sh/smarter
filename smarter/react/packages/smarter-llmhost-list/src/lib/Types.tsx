/**
 * Central type definitions for the LLMHost List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * llmhost, and API response layers. It provides strong typing for user, llmhost,
 * llmhost, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned" | "shared").
 *   - LLMHost: Type for llmhost objects.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */
import type { SessionContext, Sorting, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// LLMHost Definition
// ----------------------------------------------------------------------------

/** Inference server that loads the weights and exposes an API. */
export type InferenceEngine = "vllm" | "tgi" | "sglang" | "llama_cpp" | "ollama" | "tei" | "custom";

/** Wire-protocol contract the LLMHost endpoint speaks, independent of engine. */
export type ApiFormat = "openai_compatible" | "huggingface" | "ollama_native" | "custom";

/** Where the model weights come from. */
export type ModelSource = "huggingface" | "ollama" | "s3" | "url" | "pvc";

/** What the model does. */
export type ModelTask = "text-generation" | "embedding";

/** Numeric precision / compression scheme applied to the model's weights. */
export type Quantization =
  "none" | "fp32" | "fp16" | "bf16" | "fp8" | "mxfp4" | "int8" | "int4" | "gguf" | "awq" | "gptq";

/** Lifecycle state of the LLMHost deployment. */
export type HostStatus =
  "provisioning" | "pending" | "downloading" | "deploying" | "active" | "degraded" | "inactive" | "error";

export type LLMHost = {
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

  /** The manifest's spec, in camelCase: the source of truth for launching the LLMHost. */
  spec: Record<string, unknown>;

  // --- Model ---
  modelSource: ModelSource;
  modelRepository: string;
  modelRevision: string;
  modelTask: ModelTask;
  servedModelName: string;
  license: string;
  modelArchitecture: string;
  parameterCount: number | null;
  contextWindow: number | null;
  quantization: Quantization;
  embeddingDimensions: number | null;
  supportsStreaming: boolean;
  supportsFunctionCalling: boolean;
  supportsVision: boolean;
  supportsReasoning: boolean;

  // --- Serving ---
  inferenceEngine: InferenceEngine;
  apiFormat: ApiFormat;
  /** The id of the Smarter Secret with the API key, if any. Never the key itself. */
  apiKeySecret: number | null;

  // --- Infrastructure ---
  /** The id of the LLMHostCompute, the node group, that the LLMHost runs on. */
  compute: number | null;
  gpuType: string;
  gpuCount: number;
  vramRequiredGb: number | null;
  replicas: number;
  /** The cost per hour of one replica, its share of its compute's node, a decimal string, e.g. "1.2120". */
  costPerHour: string | null;

  // --- Observed state ---
  status: HostStatus;
  statusMessage: string;
  isActive: boolean;
  readyReplicas: number;
  /** The base URL inside the cluster. */
  endpointUrl: string;
  /** The base URL of the Ingress, if any. */
  publicUrl: string;
  healthCheckUrl: string;
  lastHealthCheckAt: string | null;
  lastHealthOk: boolean | null;
  deployedAt: string | null;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface LLMHostCardViewProps {
  sessionContext: SessionContext;
  objects: LLMHost[];
  onRequery: () => void;
}

export interface LLMHostListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: LLMHost[];
  onRequery: () => void;
  sorting?: Sorting;
}
