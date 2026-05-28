import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { promisify } from "node:util";
import type { SourceFile, SourceFileAction } from "./types";

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
  createTime?: string;
  updateTime?: string;
};

type FirestoreListResponse = {
  documents?: FirestoreDocument[];
};

const PROJECT_ID = process.env.GCP_PROJECT_ID || "capital-index-2026";
const DATABASE = process.env.FIRESTORE_DATABASE || "(default)";
const LOCAL_ACTOR = process.env.ADMIN_WEB_LOCAL_ACTOR || "local_operator";
const TOKEN_TIMEOUT_MS = 15_000;

let cachedLocalToken: { token: string; expiresAt: number } | null = null;

export async function listSourceFiles(status: string, limit: number): Promise<SourceFile[]> {
  const docs = await listCollection("files");
  const items = docs.map(sourceFileFromDocument);
  const filtered =
    status === "all" ? items : items.filter((item) => item.sourceStatus === status);
  return sortSourceFiles(filtered).slice(0, limit);
}

export async function updateSourceQuality(
  fileId: string,
  action: SourceFileAction,
  note: string,
  actorId: string | undefined,
): Promise<{
  actionId: string;
  previousSourceStatus: string;
  newSourceStatus: string;
  previousIndexEligible: boolean;
  newIndexEligible: boolean;
  previousHumanBlock: boolean;
  newHumanBlock: boolean;
}> {
  const existing = await getDocument("files", fileId);
  if (!existing) {
    throw new Error(`Source file not found: ${fileId}`);
  }

  const existingFile = sourceFileFromDocument(existing);
  const now = new Date().toISOString();
  const resolvedActor = actorId?.trim() || LOCAL_ACTOR;
  const next = nextSourceQuality(action);

  await patchDocument(
    "files",
    fileId,
    {
      source_status: stringValue(next.sourceStatus),
      index_eligible: booleanValue(next.indexEligible),
      human_block: booleanValue(next.humanBlock),
      source_quality_updated_at: timestampValue(now),
      source_quality_updated_by: stringValue(resolvedActor),
      source_quality_note: stringValue(note.trim()),
      source_approved_at:
        action === "activate"
          ? timestampValue(now)
          : existingFile.sourceApprovedAt
            ? timestampValue(existingFile.sourceApprovedAt)
            : nullValue(),
      source_approved_by:
        action === "activate"
          ? stringValue(resolvedActor)
          : existingFile.sourceApprovedBy
            ? stringValue(existingFile.sourceApprovedBy)
            : nullValue(),
    },
    [
      "source_status",
      "index_eligible",
      "human_block",
      "source_quality_updated_at",
      "source_quality_updated_by",
      "source_quality_note",
      "source_approved_at",
      "source_approved_by",
    ],
  );

  const actionId = `source_quality_${randomUUID().replace(/-/g, "").slice(0, 24)}`;
  await createDocument("source_quality_actions", actionId, {
    schema_version: stringValue("capital.source_quality_action.v1"),
    action_id: stringValue(actionId),
    file_id: stringValue(fileId),
    actor_id: stringValue(resolvedActor),
    actor_type: stringValue("human_operator"),
    action: stringValue(action),
    previous_source_status: stringValue(existingFile.sourceStatus),
    new_source_status: stringValue(next.sourceStatus),
    previous_index_eligible: booleanValue(existingFile.indexEligible),
    new_index_eligible: booleanValue(next.indexEligible),
    previous_human_block: booleanValue(existingFile.humanBlock),
    new_human_block: booleanValue(next.humanBlock),
    drive_mutation: stringValue("none"),
    drive_mutation_allowed: booleanValue(false),
    policy_snapshot_id: nullValue(),
    approval_decision_id: nullValue(),
    note: stringValue(note.trim()),
    created_at: timestampValue(now),
  });

  return {
    actionId,
    previousSourceStatus: existingFile.sourceStatus,
    newSourceStatus: next.sourceStatus,
    previousIndexEligible: existingFile.indexEligible,
    newIndexEligible: next.indexEligible,
    previousHumanBlock: existingFile.humanBlock,
    newHumanBlock: next.humanBlock,
  };
}

function sourceFileFromDocument(doc: FirestoreDocument): SourceFile {
  const fields = doc.fields || {};
  return {
    fileId: readString(fields.file_id) || doc.name.split("/").pop() || "",
    name: readString(fields.name),
    mimeType: readString(fields.mime_type),
    projectId: readNullableString(fields.project_id),
    sourceRegistryId: readNullableString(fields.source_registry_id),
    sourceStatus: readString(fields.source_status) || "needs_human_review",
    indexEligible: readBoolean(fields.index_eligible),
    humanBlock: readBoolean(fields.human_block),
    metadataStatus: readString(fields.metadata_status),
    modifiedTime: readString(fields.modified_time) || readTimestamp(fields.modified_time),
    webViewLink: readString(fields.web_view_link),
    sourceApprovedAt: readString(fields.source_approved_at) || readTimestamp(fields.source_approved_at),
    sourceApprovedBy: readString(fields.source_approved_by),
    sourceQualityUpdatedAt:
      readString(fields.source_quality_updated_at) || readTimestamp(fields.source_quality_updated_at),
  };
}

function sortSourceFiles(items: SourceFile[]): SourceFile[] {
  const rank: Record<string, number> = {
    needs_human_review: 0,
    candidate_empty: 1,
    candidate_duplicate: 2,
    candidate_stale: 3,
    candidate_archive: 4,
    do_not_index: 5,
    active: 6,
  };
  return [...items].sort((a, b) => {
    const rankDiff = (rank[a.sourceStatus] ?? 9) - (rank[b.sourceStatus] ?? 9);
    if (rankDiff !== 0) return rankDiff;
    return (b.modifiedTime || "").localeCompare(a.modifiedTime || "");
  });
}

function nextSourceQuality(action: SourceFileAction): {
  sourceStatus: string;
  indexEligible: boolean;
  humanBlock: boolean;
} {
  switch (action) {
    case "activate":
      return { sourceStatus: "active", indexEligible: true, humanBlock: false };
    case "do_not_index":
      return { sourceStatus: "do_not_index", indexEligible: false, humanBlock: true };
    case "needs_review":
    default:
      return { sourceStatus: "needs_human_review", indexEligible: false, humanBlock: false };
  }
}

async function listCollection(collection: string): Promise<FirestoreDocument[]> {
  const token = await accessToken();
  const response = await fetch(`${baseUrl()}/${collection}?pageSize=300`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (response.status === 404) {
    return [];
  }
  if (!response.ok) {
    throw new Error(`Firestore list failed: ${response.status} ${await response.text()}`);
  }
  const data = (await response.json()) as FirestoreListResponse;
  return data.documents || [];
}

async function getDocument(collection: string, id: string): Promise<FirestoreDocument | null> {
  const token = await accessToken();
  const response = await fetch(`${baseUrl()}/${collection}/${encodeURIComponent(id)}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Firestore get failed: ${response.status} ${await response.text()}`);
  }
  return (await response.json()) as FirestoreDocument;
}

async function patchDocument(
  collection: string,
  id: string,
  fields: Record<string, FirestoreValue>,
  updateMask: string[],
): Promise<void> {
  const token = await accessToken();
  const params = new URLSearchParams();
  updateMask.forEach((field) => params.append("updateMask.fieldPaths", field));

  const response = await fetch(
    `${baseUrl()}/${collection}/${encodeURIComponent(id)}?${params.toString()}`,
    {
      method: "PATCH",
      headers: { ...authHeaders(token), "content-type": "application/json" },
      body: JSON.stringify({ fields }),
    },
  );
  if (!response.ok) {
    throw new Error(`Firestore patch failed: ${response.status} ${await response.text()}`);
  }
}

async function createDocument(
  collection: string,
  id: string,
  fields: Record<string, FirestoreValue>,
): Promise<void> {
  const token = await accessToken();
  const response = await fetch(`${baseUrl()}/${collection}?documentId=${encodeURIComponent(id)}`, {
    method: "POST",
    headers: { ...authHeaders(token), "content-type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!response.ok) {
    throw new Error(`Firestore create failed: ${response.status} ${await response.text()}`);
  }
}

function baseUrl(): string {
  return `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/${encodeURIComponent(DATABASE)}/documents`;
}

function authHeaders(token: string): HeadersInit {
  return { authorization: `Bearer ${token}` };
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

function readTimestamp(value: FirestoreValue | undefined): string {
  return value && "timestampValue" in value ? value.timestampValue : "";
}

function readBoolean(value: FirestoreValue | undefined): boolean {
  return Boolean(value && "booleanValue" in value && value.booleanValue);
}

function stringValue(value: string): FirestoreValue {
  return { stringValue: value };
}

function timestampValue(value: string): FirestoreValue {
  return { timestampValue: value };
}

function booleanValue(value: boolean): FirestoreValue {
  return { booleanValue: value };
}

function nullValue(): FirestoreValue {
  return { nullValue: null };
}
