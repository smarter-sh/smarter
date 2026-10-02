/**
 * Formatting of LLMHostCompute attributes, shared by ListView, CardView and StatusBar.
 */
import type { LLMHostCompute } from "@/lib/Types";

/** The node's GPUs, e.g. "1 × L4, 24 GB", or "CPU only". */
export function formatGpus(compute: LLMHostCompute): string {
  if (!compute.gpuCount) return "CPU only";
  return `${compute.gpuCount} × ${compute.gpuType}, ${compute.gpuMemoryGb} GB`;
}

/** The node's CPU and memory, e.g. "8 vCPU, 32 GiB". */
export function formatCpuMemory(compute: LLMHostCompute): string {
  return `${compute.cpu} vCPU, ${compute.memoryGb} GiB`;
}

/** The price of one node, e.g. "$0.98/hr". */
export function formatPrice(compute: LLMHostCompute): string {
  if (compute.pricePerHour === null || compute.pricePerHour === undefined) return "—";
  return `$${Number(compute.pricePerHour).toFixed(2)}/hr`;
}

/** The node group's nodes, e.g. "1 of 1 ready, max 4". */
export function formatNodes(compute: LLMHostCompute): string {
  return `${compute.readyNodes} of ${compute.desiredNodes} ready, max ${compute.maxNodes}`;
}
