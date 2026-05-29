import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { KnowledgeEntity, KnowledgeItem, KnowledgeRelationship, ProgressSummary } from "./types";

const execFileAsync = promisify(execFile);

type FirestoreValue =
  | { stringValue: string }
  | { integerValue: string }
  | { doubleValue: number }
  | { booleanValue: boolean }
  | { timestampValue: string }
  | { arrayValue: { values?: FirestoreValue[] } }
  | { mapValue: { fields?: Record<string, FirestoreValue> } }
  | { nullValue: null };

type FirestoreDocument = {
  name: string;
  fields?: Record<string, FirestoreValue>;
};

type FirestoreListResponse = {
  documents?: FirestoreDocument[];
  nextPageToken?: string;
};

const PROJECT_ID = process.env.GCP_PROJECT_ID || "capital-index-2026";
const DATABASE = process.env.FIRESTORE_DATABASE || "(default)";
const TOKEN_TIMEOUT_MS = 15_000;

let cachedLocalToken: { token: string; expiresAt: number } | null = null;

export async function listKnowledgeItems(limit: number): Promise<KnowledgeItem[]> {
  const [extractedDocs, extractionDocs, fileDocs] = await Promise.all([
    listCollection("extracted_text", Math.max(limit, 100)),
    listCollection("entity_extractions", Math.max(limit, 100)),
    listCollection("files", 10_000),
  ]);
  const filesById = new Map(fileDocs.map((doc) => [doc.name.split("/").pop() || "", doc]));
  const extractionsByFileId = new Map<string, FirestoreDocument>();
  extractionDocs.forEach((doc) => {
    const fileId = readString(doc.fields?.file_id);
    if (fileId && !extractionsByFileId.has(fileId)) {
      extractionsByFileId.set(fileId, doc);
    }
  });

  return extractedDocs
    .map((doc) => knowledgeItemFromDocuments(doc, extractionsByFileId, filesById))
    .sort((a, b) => (b.extractedAt || "").localeCompare(a.extractedAt || ""))
    .slice(0, limit);
}

export async function getProgressSummary(): Promise<ProgressSummary> {
  const [fileDocs, extractedDocs, extractionDocs, cleanupDocs, reviewDocs] = await Promise.all([
    listCollection("files", 10_000),
    listCollection("extracted_text", 1000),
    listCollection("entity_extractions", 1000),
    listCollection("cleanup_queue", 1000),
    listCollection("review_queue", 1000),
  ]);
  const sourceStatuses = fileDocs.map((doc) => readString(doc.fields?.source_status) || "unknown");
  const extractionStatuses = extractionDocs.map((doc) => readString(doc.fields?.status) || "unknown");
  return {
    filesTotal: fileDocs.length,
    active: sourceStatuses.filter((status) => status === "active").length,
    doNotIndex: sourceStatuses.filter((status) => status === "do_not_index").length,
    needsHumanReview: sourceStatuses.filter((status) => status === "needs_human_review" || status === "unknown")
      .length,
    cleanupCandidates: sourceStatuses.filter((status) => status.startsWith("candidate_")).length,
    extractedText: extractedDocs.length,
    entityExtractions: extractionDocs.length,
    understood: extractionStatuses.filter((status) => status === "extracted").length,
    needsEntityReview: extractionStatuses.filter((status) => status === "needs_review").length,
    cleanupOpen: cleanupDocs.filter((doc) => readString(doc.fields?.status) === "open").length,
    reviewOpen: reviewDocs.filter((doc) => readString(doc.fields?.status) === "open").length,
  };
}

function knowledgeItemFromDocuments(
  extractedDoc: FirestoreDocument,
  extractionsByFileId: Map<string, FirestoreDocument>,
  filesById: Map<string, FirestoreDocument>,
): KnowledgeItem {
  const fields = extractedDoc.fields || {};
  const fileId = readString(fields.file_id) || extractedDoc.name.split("/").pop() || "";
  const fileFields = filesById.get(fileId)?.fields || {};
  const extractionFields = extractionsByFileId.get(fileId)?.fields || {};
  const text = readString(fields.text);
  const entities = readArray(extractionFields.entities).map(entityFromValue);
  const relationships = readArray(extractionFields.relationships).map(relationshipFromValue);
  return {
    fileId,
    title: readString(fields.doc_title) || readString(fileFields.name) || fileId,
    projectId: readNullableString(fields.project_id) || readNullableString(fileFields.project_id),
    sourceStatus: readString(fileFields.source_status) || "unknown",
    indexEligible: readBoolean(fileFields.index_eligible),
    charCount: readNumber(fields.char_count),
    nextAction: readString(fields.next_action),
    extractedAt: readString(fields.extracted_at) || readString(fields.written_at),
    preview: text.slice(0, 2000),
    extractionStatus: readString(extractionFields.status) || "not_extracted",
    entityCount: entities.length,
    relationshipCount: relationships.length,
    entities,
    relationships,
    issues: readArray(extractionFields.issues).map(readString),
  };
}

function entityFromValue(value: FirestoreValue): KnowledgeEntity {
  const fields = "mapValue" in value ? value.mapValue.fields || {} : {};
  return {
    entityType: readString(fields.entity_type) || readString(fields.type),
    name: readString(fields.name),
    confidence: readNumber(fields.confidence),
    evidence: readString(fields.evidence),
  };
}

function relationshipFromValue(value: FirestoreValue): KnowledgeRelationship {
  const fields = "mapValue" in value ? value.mapValue.fields || {} : {};
  return {
    relationshipType: readString(fields.relationship_type) || readString(fields.type),
    from: readString(fields.from_id) || readString(fields.from),
    to: readString(fields.to_id) || readString(fields.to),
    confidence: readNumber(fields.confidence),
    reason: readString(fields.reason),
  };
}

async function listCollection(collection: string, pageSize: number): Promise<FirestoreDocument[]> {
  const token = await accessToken();
  const documents: FirestoreDocument[] = [];
  let pageToken = "";
  do {
    const params = new URLSearchParams({ pageSize: String(Math.min(pageSize, 1000)) });
    if (pageToken) params.set("pageToken", pageToken);
    const response = await fetch(`${baseUrl()}/${collection}?${params.toString()}`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (response.status === 404) {
      return documents;
    }
    if (!response.ok) {
      throw new Error(`Firestore list failed: ${response.status} ${await response.text()}`);
    }
    const data = (await response.json()) as FirestoreListResponse;
    documents.push(...(data.documents || []));
    pageToken = data.nextPageToken || "";
  } while (pageToken && documents.length < pageSize);
  return documents.slice(0, pageSize);
}

function baseUrl(): string {
  return `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/${encodeURIComponent(DATABASE)}/documents`;
}

async function accessToken(): Promise<string> {
  if (process.env.GOOGLE_OAUTH_ACCESS_TOKEN) {
    return process.env.GOOGLE_OAUTH_ACCESS_TOKEN;
  }
  if (process.env.K_SERVICE) {
    const response = await fetch(
      "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
      { headers: { "Metadata-Flavor": "Google" }, cache: "no-store" },
    );
    if (!response.ok) {
      throw new Error(`Metadata token failed: ${response.status} ${await response.text()}`);
    }
    const data = (await response.json()) as { access_token?: string };
    if (!data.access_token) {
      throw new Error("Metadata token response did not include access_token");
    }
    return data.access_token;
  }
  return localGcloudAccessToken();
}

async function localGcloudAccessToken(): Promise<string> {
  if (cachedLocalToken && cachedLocalToken.expiresAt > Date.now()) {
    return cachedLocalToken.token;
  }
  const { stdout } = await execFileAsync(
    "gcloud",
    ["auth", "application-default", "print-access-token"],
    { timeout: TOKEN_TIMEOUT_MS },
  );
  cachedLocalToken = { token: stdout.trim(), expiresAt: Date.now() + 45 * 60 * 1000 };
  return cachedLocalToken.token;
}

function readArray(value: FirestoreValue | undefined): FirestoreValue[] {
  return value && "arrayValue" in value ? value.arrayValue.values || [] : [];
}

function readString(value: FirestoreValue | undefined): string {
  if (!value) return "";
  if ("stringValue" in value) return value.stringValue;
  if ("timestampValue" in value) return value.timestampValue;
  if ("integerValue" in value) return value.integerValue;
  if ("doubleValue" in value) return String(value.doubleValue);
  if ("booleanValue" in value) return String(value.booleanValue);
  return "";
}

function readNullableString(value: FirestoreValue | undefined): string | null {
  if (!value || "nullValue" in value) return null;
  return readString(value);
}

function readBoolean(value: FirestoreValue | undefined): boolean {
  return Boolean(value && "booleanValue" in value && value.booleanValue);
}

function readNumber(value: FirestoreValue | undefined): number {
  if (!value) return 0;
  if ("integerValue" in value) return Number(value.integerValue);
  if ("doubleValue" in value) return value.doubleValue;
  return Number(readString(value)) || 0;
}
