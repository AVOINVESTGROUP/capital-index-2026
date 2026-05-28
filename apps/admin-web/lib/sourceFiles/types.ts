export type SourceFileStatus =
  | "active"
  | "candidate_duplicate"
  | "candidate_stale"
  | "candidate_empty"
  | "candidate_archive"
  | "do_not_index"
  | "needs_human_review";

export type SourceFileAction = "activate" | "needs_review" | "do_not_index";

export type SourceFile = {
  fileId: string;
  name: string;
  mimeType: string;
  projectId: string | null;
  sourceRegistryId: string | null;
  sourceStatus: SourceFileStatus | string;
  indexEligible: boolean;
  humanBlock: boolean;
  metadataStatus: string;
  modifiedTime: string;
  webViewLink: string;
  sourceApprovedAt: string;
  sourceApprovedBy: string;
  sourceQualityUpdatedAt: string;
};

export type SourceFilesListResponse = {
  items: SourceFile[];
  status: string;
  count: number;
  generatedAt: string;
};

export type SourceFileActionRequest = {
  action: SourceFileAction;
  note?: string;
};
