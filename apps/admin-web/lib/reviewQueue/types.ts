export type ReviewStatus = "open" | "approved" | "rejected" | "needs_content" | "closed";

export type ReviewAction = "approve" | "reject" | "needs_content" | "close" | "reopen";

export type ReviewItem = {
  reviewId: string;
  status: ReviewStatus | string;
  priority: string;
  reason: string;
  fileId: string;
  docTitle: string;
  sensitivityClass: string;
  source: string;
  sourceCollection: string;
  sourceDecisionId: string;
  traceId: string;
  nextAction: string;
  charCount: number | null;
  createdAt: string;
  updatedAt: string;
  reviewedAt?: string;
  reviewedBy?: string;
  reviewNote?: string;
};

export type ReviewListResponse = {
  items: ReviewItem[];
  status: string;
  count: number;
  generatedAt: string;
};

export type ReviewActionRequest = {
  action: ReviewAction;
  note?: string;
  actorId?: string;
};

export type ReviewActionResponse = {
  ok: true;
  reviewId: string;
  actionId: string;
  previousStatus: string;
  newStatus: string;
};

export type ReviewActionLog = {
  actionId: string;
  actorId: string;
  actorType: string;
  source: string;
  targetId: string;
  previousStatus: string;
  newStatus: string;
  reason: string;
  note: string;
  createdAt: string;
};

export type ReviewActionsResponse = {
  actions: ReviewActionLog[];
  reviewId: string;
  count: number;
  generatedAt: string;
};
