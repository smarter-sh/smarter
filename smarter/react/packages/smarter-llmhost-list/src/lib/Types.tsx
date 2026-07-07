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
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// LLMHost Definition
// ----------------------------------------------------------------------------

/** Model-serving backend responsible for loading weights and exposing an API. */
export type InferenceEngine =
  | "vllm"
  | "tgi"
  | "ollama"
  | "llama_cpp"
  | "sglang"
  | "transformers"
  | "triton"
  | "custom";

/** Wire-protocol contract the LLMHost endpoint speaks, independent of engine. */
export type ApiFormat =
  | "openai_compatible"
  | "huggingface"
  | "ollama_native"
  | "custom";

/** Numeric precision / compression scheme applied to the model's weights. */
export type Quantization =
  | "none"
  | "fp16"
  | "bf16"
  | "int8"
  | "int4"
  | "gguf"
  | "awq"
  | "gptq";

/** Infrastructure substrate the LLMHost is deployed on. */
export type DeploymentType =
  | "docker"
  | "kubernetes"
  | "bare_metal"
  | "cloud_instance";

/** Cloud (or non-cloud) provider hosting the deployment. Required when deploymentType is "cloud_instance". */
export type CloudProvider = "aws" | "gcp" | "azure" | "on_prem" | "other";

/** Lifecycle state of the LLMHost deployment. */
export type HostStatus =
  | "pending"
  | "downloading"
  | "deploying"
  | "active"
  | "degraded"
  | "inactive"
  | "error"
  | "deprecated";

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
  ready: boolean;
  rfc1034CompliantName: string | null;

  // --- Provenance ---
  huggingfaceRepoId: string;
  huggingfaceRevision: string;
  license: string;
  modelArchitecture: string;

  // --- Characteristics ---
  parameterCount: number | null;
  contextWindow: number | null;
  quantization: Quantization;
  embeddingDimensions: number | null;
  supportsStreaming: boolean;
  supportsFunctionCalling: boolean;
  supportsVision: boolean;

  // --- Serving ---
  inferenceEngine: InferenceEngine;
  apiFormat: ApiFormat;
  endpointUrl: string;
  /** Secret reference, not a plaintext credential — resolved server-side against the account's secret store. */
  apiKey: string;
  engineConfig: Record<string, unknown>;

  // --- Infrastructure ---
  deploymentType: DeploymentType;
  cloudProvider: CloudProvider | "";
  region: string;
  instanceType: string;
  gpuType: string;
  gpuCount: number;
  vramRequiredGb: number | null;
  costPerHour: number | null;

  // --- Health / lifecycle ---
  /** Renamed from the spec's `status` to avoid colliding with the LLMConnectionStatus field above. */
  hostStatus: HostStatus;
  isActive: boolean;
  healthCheckUrl: string;
  lastHealthOk: boolean | null;
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
}
