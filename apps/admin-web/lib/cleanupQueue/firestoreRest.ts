import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { promisify } from "node:util";
import type { CleanupAction, CleanupItem } from "./types";

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

export async function listCleanupItems(status: string, limit: number): Promise<CleanupItem[]> {
  const docs = await listCollection("cleanup_queue");
  const items = docs.map(cleanupItemFromDocument);
  const filtered = status === "all" ? items : items.filter((item) => item.status === status);
  return sortCleanupItems(filtered).slice(0, limit);
}

export async function updateCleanupItem(
  cleanupId: string,
  action: CleanupAction,
  note: string,
  actorId: string | undefined,
): Promise<{
  actionId: string;
  previousStatus: string;
  newStatus: string;
  previousSourceStatus: string;
  newSourceStatus: string;
}> {
  const existing = await getDocument("cleanup_queue", cleanupId);
  if (!existing) {
    throw new Error(`Cleanup item not found: ${cleanupId}`);
  }

  const existingItem = cleanupItemFromDocument(existing);
  const now = new Date().toISOString();
  const resolvedActor = actorId?.trim() || LOCAL_ACTOR;
  const newStatus = statusForAction(action);
  const newSourceStatus = sourceStatusForAction(action, existingItem.sourceStatus);

  await patchDocument(
    "cleanup_queue",
    cleanupId,
    {
      status: stringValue(newStatus),
      resolved_at: timestampValue(now),
      resolved_by: stringValue(resolvedActor),
    },
    ["status", "resolved_at", "resolved_by"],
  );

  const actionId = `cleanup_action_${randomUUID().replace(/-/g, "").slice(0, 24)}`;
  await createDocument("cleanup_actions", actionId, {
    schema_version: stringValue("capital.cleanup_action.v1"),
    action_id: stringValue(actionId),
    cleanup_id: stringValue(cleanupId),
    file_id: stringValue(existingItem.fileId),
    actor_id: stringValue(resolvedActor),
    actor_type: stringValue("human_operator"),
    action: stringValue(action),
    previous_source_status: stringValue(existingItem.sourceStatus),
    new_source_status: stringValue(newSourceStatus),
    drive_mutation: stringValue("none"),
    drive_mutation_allowed: booleanValue(false),
    policy_snapshot_id: nullValue(),
    approval_decision_id: nullValue(),
    note: stringValue(note.trim()),
    created_at: timestampValue(now),
  });

  return {
    actionId,
    previousStatus: existingItem.status,
    newStatus,
    previousSourceStatus: existingItem.sourceStatus,
    newSourceStatus,
  };
}

function cleanupItemFromDocument(doc: FirestoreDocument): CleanupItem {
  const fields = doc.fields || {};
  const evidence = readMap(fields.evidence);
  return {
    cleanupId: readString(fields.cleanup_id) || doc.name.split("/").pop() || "",
    fileId: readString(fields.file_id),
    projectId: readNullableString(fields.project_id),
    sourceRegistryId: readNullableString(fields.source_registry_id),
    sourceStatus: readString(fields.source_status),
    reason: readString(fields.reason),
    recommendedAction: readString(fields.recommended_action),
    confidence: readNumber(fields.confidence),
    evidenceSignals: readStringArray(evidence.signals),
    matchedFileIds: readStringArray(evidence.matched_file_ids),
    ageDays: readInteger(evidence.age_days),
    modifiedAt: readString(evidence.modified_at) || readTimestamp(evidence.modified_at),
    size: readInteger(evidence.size),
    humanApprovalRequired: readBoolean(fields.human_approval_required),
    status: readString(fields.status) || "open",
    createdAt: readString(fields.created_at) || readTimestamp(fields.created_at) || doc.createTime || "",
    resolvedAt: readString(fields.resolved_at) || readTimestamp(fields.resolved_at),
    resolvedBy: readString(fields.resolved_by),
  };
}

function sortCleanupItems(items: CleanupItem[]): CleanupItem[] {
  const rank: Record<string, number> = {
    needs_human_review: 0,
    candidate_duplicate: 1,
    candidate_stale: 2,
    candidate_empty: 3,
    candidate_archive: 4,
  };
  return [...items].sort((a, b) => {
    const rankDiff = (rank[a.sourceStatus] ?? 9) - (rank[b.sourceStatus] ?? 9);
    if (rankDiff !== 0) {
      return rankDiff;
    }
    return (b.confidence ?? 0) - (a.confidence ?? 0);
  });
}

function statusForAction(action: CleanupAction): string {
  return action === "ignore" ? "ignored" : "approved";
}

function sourceStatusForAction(action: CleanupAction, current: string): string {
  switch (action) {
    case "keep_active":
      return "active";
    case "mark_duplicate":
      return "candidate_duplicate";
    case "archive":
      return "candidate_archive";
    case "move_to_review":
      return "needs_human_review";
    case "do_not_index":
      return "do_not_index";
    case "ignore":
      return current;
    default:
      return current;
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

function readInteger(value: FirestoreValue | undefined): number | null {
  if (!value || "nullValue" in value) return null;
  if ("integerValue" in value) return Number.parseInt(value.integerValue, 10);
  if ("doubleValue" in value) return Math.trunc(value.doubleValue);
  return null;
}

function readNumber(value: FirestoreValue | undefined): number | null {
  if (!value || "nullValue" in value) return null;
  if ("doubleValue" in value) return value.doubleValue;
  if ("integerValue" in value) return Number.parseInt(value.integerValue, 10);
  return null;
}

function readBoolean(value: FirestoreValue | undefined): boolean {
  return Boolean(value && "booleanValue" in value && value.booleanValue);
}

function readMap(value: FirestoreValue | undefined): Record<string, FirestoreValue | undefined> {
  return value && "mapValue" in value ? value.mapValue.fields || {} : {};
}

function readStringArray(value: FirestoreValue | undefined): string[] {
  if (!value || !("arrayValue" in value)) return [];
  return (value.arrayValue.values || []).map(readString).filter(Boolean);
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
