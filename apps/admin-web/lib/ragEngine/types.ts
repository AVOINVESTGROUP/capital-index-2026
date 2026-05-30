export type RagFile = {
  name: string;
  displayName: string;
  createTime: string;
  updateTime: string;
};

export type RagEngineState = {
  generatedAt: string;
  projectId: string;
  location: string;
  corpusId: string;
  corpusName: string;
  displayName: string;
  promptName: string;
  driveSource: string;
  agentStudioUrl: string;
  ragConsoleUrl: string;
  fileCount: number;
  files: RagFile[];
  status: "ready" | "not_configured" | "error";
  error?: string;
};
