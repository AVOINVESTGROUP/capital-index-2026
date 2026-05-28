export type KnowledgeEntity = {
  entityType: string;
  name: string;
  confidence: number;
  evidence: string;
};

export type KnowledgeRelationship = {
  relationshipType: string;
  from: string;
  to: string;
  confidence: number;
  reason: string;
};

export type KnowledgeItem = {
  fileId: string;
  title: string;
  projectId: string | null;
  sourceStatus: string;
  indexEligible: boolean;
  charCount: number;
  nextAction: string;
  extractedAt: string;
  preview: string;
  extractionStatus: string;
  entityCount: number;
  relationshipCount: number;
  entities: KnowledgeEntity[];
  relationships: KnowledgeRelationship[];
  issues: string[];
};

export type KnowledgeListResponse = {
  items: KnowledgeItem[];
  count: number;
  generatedAt: string;
};

export type ProgressSummary = {
  filesTotal: number;
  active: number;
  doNotIndex: number;
  needsHumanReview: number;
  cleanupCandidates: number;
  extractedText: number;
  entityExtractions: number;
  understood: number;
  needsEntityReview: number;
  cleanupOpen: number;
  reviewOpen: number;
};

export type ProgressSummaryResponse = {
  summary: ProgressSummary;
  generatedAt: string;
};
