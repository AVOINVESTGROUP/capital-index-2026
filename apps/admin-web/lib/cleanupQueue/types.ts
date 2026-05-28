export type CleanupStatus = "open" | "approved" | "rejected" | "ignored" | "applied";

export type CleanupAction =
  | "keep_active"
  | "mark_duplicate"
  | "archive"
  | "move_to_review"
  | "do_not_index"
  | "ignore";

export type CleanupItem = {
  cleanupId: string;
  fileId: string;
  projectId: string | null;
  sourceRegistryId: string | null;
  sourceStatus: string;
  reason: string;
  recommendedAction: string;
  confidence: number | null;
  evidenceSignals: string[];
  matchedFileIds: string[];
  ageDays: number | null;
  modifiedAt: string;
  size: number | null;
  humanApprovalRequired: boolean;
  status: CleanupStatus | string;
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
};

export type CleanupListResponse = {
  items: CleanupItem[];
  status: string;
  count: number;
  generatedAt: string;
};

export type CleanupActionRequest = {
  action: CleanupAction;
  note?: string;
};

export type CleanupActionLog = {
  actionId: string;
  cleanupId: string;
  fileId: string;
  actorId: string;
  actorType: string;
  action: string;
  previousSourceStatus: string;
  newSourceStatus: string;
  driveMutation: string;
  driveMutationAllowed: boolean;
  note: string;
  createdAt: string;
};
