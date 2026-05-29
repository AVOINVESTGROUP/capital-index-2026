export type ContextBundleStatus = "draft" | "approved" | "rejected" | "superseded";

export type ContextBundleAction = "approve" | "reject" | "supersede";

export type ContextBundle = {
  bundleId: string;
  bundleType: string;
  approvalStatus: ContextBundleStatus | string;
  requiresHumanApproval: boolean;
  createdAt: string;
  createdBy: string;
  approvedAt: string;
  approvedBy: string;
  sourceFileCount: number;
  claimCount: number;
  entityCount: number;
  relationshipCount: number;
  evidenceCount: number;
  actualBundleBytes: number;
  maxBundleBytes: number;
  sourceFileIds: string[];
  omittedCount: number;
  recentClaims: Array<{
    claimId: string;
    claimType: string;
    text: string;
    confidence: number;
    evidenceIds: string[];
    sourceFileIds: string[];
  }>;
  relationships: Array<{
    relationshipId: string;
    relationshipType: string;
    fromId: string;
    toId: string;
    confidence: number;
    evidenceIds: string[];
  }>;
  vaultProjection?: {
    projectionId: string;
    path: string;
    title: string;
    content: string;
    writeStatus: string;
    requiresApproval: boolean;
  };
};

export type ContextBundleActionRequest = {
  action: ContextBundleAction;
  note?: string;
};

export type ContextBundleListResponse = {
  items: ContextBundle[];
  count: number;
  generatedAt: string;
};
