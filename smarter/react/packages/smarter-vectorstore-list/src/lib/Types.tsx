/**
 * Central type definitions for the Vectorstore List React application.
 *
 * Vectorstore mirrors smarter.apps.vectorstore.serializers.VectorstoreSerializer, whose JSON field
 * names are camelCase. Related objects are given by name, and a Secret's value is never included.
 */
import type { SessionContext, Annotations, Tags, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Vectorstore Definition
// ----------------------------------------------------------------------------
export type VectorstoreBackend = "qdrant" | "pinecone";
export type VectorstoreHosting = "self_hosted" | "managed";
export type VectorstoreMetric = "cosine" | "euclidean" | "dotproduct";
export type VectorstoreStatus = "pending" | "provisioning" | "ready" | "stopped" | "failed" | "deleting";

export type Vectorstore = {
  // --- MetaDataWithOwnershipModel ---
  id: number;
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: Tags;
  annotations: Annotations;
  userProfile: UserProfile;
  manifestUrl: string;
  canDelete: boolean; // false if other resources depend on it, or you may not delete it

  // --- the manifest ---
  spec: Record<string, unknown>;
  backend: VectorstoreBackend;
  hosting: VectorstoreHosting;
  connection: string | null; // an ApiConnection's name
  isActive: boolean;
  dimension: number;
  metric: VectorstoreMetric;
  deletionProtection: boolean;
  embeddingsProvider: string | null; // a Provider's name
  embeddingsModel: string;

  // --- state ---
  status: VectorstoreStatus;
  statusMessage: string;
  indexName: string;
  endpointUrl: string;
  apiKeySecret: string | null; // a Secret's name, never its value
  vectorCount: number;
  documentCount: number;
  snapshotCount: number;
  stats: Record<string, unknown>;
  deployedAt: string | null;
  lastCheckedAt: string | null;
  lastSnapshotAt: string | null;
  lastMaintenanceAt: string | null;
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface VectorstoreCardViewProps {
  sessionContext: SessionContext;
  objects: Vectorstore[];
  onRequery: () => void;
}

export interface VectorstoreListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: Vectorstore[];
  onRequery: () => void;
}
