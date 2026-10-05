/**
 * Central type definitions for the Custom Domain List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the CardView,
 * ListView, and API response layers.
 *
 * Exports:
 *   - CustomDomain: Type for custom domain objects.
 *   - CustomDomainLLMClient: Type for the llmclient that a custom domain serves.
 *   - CustomDomainDnsRecord: Type for a custom domain's DNS records.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 *
 * See smarter.apps.llmclient.serializers.LLMClientCustomDomainListSerializer.
 */
import type { SessionContext, Annotations, UserProfile } from "@smarter/common";

// ----------------------------------------------------------------------------
// Custom Domain Definition
// ----------------------------------------------------------------------------
export type CustomDomainLLMClient = {
  id: number;
  name: string;
  deployed: boolean;
  url: string | null; // the llmclient's url on this custom domain
  sandboxUrl: string;
  manifestUrl: string;
  owner: string;
};

export type CustomDomainDnsRecord = {
  name: string;
  type: string;
  value: string;
  ttl: number | null;
};

export type CustomDomainVerificationStatus = "Not Verified" | "Verifying" | "Verified" | "Failed";

export type CustomDomain = {
  id: number;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: string[];
  annotations: Annotations[];
  userProfile: UserProfile;
  manifestUrl: string;
  canDelete: boolean; // false if an LLMClient uses it, or you may not delete it
  domainName: string;
  awsHostedZoneId: string;
  verificationStatus: CustomDomainVerificationStatus;
  verifiedAt: string | null;
  verificationMessage: string; // why the domain is not verified yet, or why verification failed
  llmclient: CustomDomainLLMClient | null;
  dnsRecords: CustomDomainDnsRecord[];
};

// ----------------------------------------------------------------------------
// Component Props Interfaces
// ----------------------------------------------------------------------------
export interface CustomDomainCardViewProps {
  sessionContext: SessionContext;
  objects: CustomDomain[];
  onRequery: () => void;
}

export interface CustomDomainListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  objects: CustomDomain[];
  onRequery: () => void;
}
