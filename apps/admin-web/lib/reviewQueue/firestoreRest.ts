import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { promisify } from "node:util";
import type { ReviewAction, ReviewActionLog, ReviewItem } from "./types";

const execFileAsync = promisify(execFile);

type FirestoreValue =
  | { stringValue: string }
  | { integerValue: string }
  | { booleanValue: boolean }
  | { timestampValue: string }
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

export async function listReviewItems(status: string, limit: number): Promise<ReviewItem[]> {
  const docs = await listCollection("review_queue");
  const items = docs.map(reviewItemFromDocument);
  const filtered = status === "all" ? items : items.filter((item) => item.status === status);
  return sortReviewItems(filtered).slice(0, limit);
}

export async function listReviewActions(reviewId: string): Promise<ReviewActionLog[]> {
  const docs = await listCollection("review_actions");
  return docs
    .map(reviewActionFromDocument)
    .filter((action) => action.targetId === reviewId)
    .sort((a, b) => (b.createdAt || b.actionId).localeCompare(a.createdAt || a.actionId));
}

export async function updateReviewItem(
  reviewId: string,
  action: ReviewAction,
  note: string,
  actorId: string | undefined,
): Promise<{
  actionId: string;
  previousStatus: string;
  newStatus: string;
}> {
  const existing = await getDocument("review_queue", reviewId);
  if (!existing) {
    throw new Error(`Review item not found: ${reviewId}`);
  }

  const existingItem = reviewItemFromDocument(existing);
  const newStatus = statusForAction(action);
  const now = new Date().toISOString();
  const resolvedActor = actorId?.trim() || LOCAL_ACTOR;

  await patchDocument(
    "review_queue",
    reviewId,
    {
      status: stringValue(newStatus),
      reviewed_at: timestampValue(now),
      reviewed_by: stringValue(resolvedActor),
      review_note: stringValue(note.trim()),
      updated_at: timestampValue(now),
    },
    ["status", "reviewed_at", "reviewed_by", "review_note", "updated_at"],
  );

  const actionId = `review_action_${randomUUID().replace(/-/g, "")}`;
  await createDocument("review_actions", actionId, {
    action_id: stringValue(actionId),
    actor_id: stringValue(resolvedActor),
    actor_type: stringValue("human_operator"),
    source: stringValue("admin-web"),
    target_collection: stringValue("review_queue"),
    target_id: stringValue(reviewId),
    previous_status: stringValue(existingItem.status || ""),
    new_status: stringValue(newStatus),
    reason: stringValue(action),
    note: stringValue(note.trim()),
    created_at: timestampValue(now),
  });

  return {
    actionId,
    previousStatus: existingItem.status,
    newStatus,
  };
}

function reviewItemFromDocument(doc: FirestoreDocument): ReviewItem {
  const fields = doc.fields || {};
  const fallbackId = doc.name.split("/").pop() || "";
  return {
    reviewId: readString(fields.review_id) || fallbackId,
    status: readString(fields.status) || "open",
    priority: readString(fields.priority) || "normal",
    reason: readString(fields.reason) || "review_required",
    fileId: readString(fields.file_id),
    docTitle: readString(fields.doc_title),
    sensitivityClass: readString(fields.sensitivity_class),
    source: readString(fields.source),
    sourceCollection: readString(fields.source_collection),
    sourceDecisionId: readString(fields.source_decision_id),
    traceId: readString(fields.trace_id),
    nextAction: readString(fields.next_action),
    charCount: readInteger(fields.char_count),
    createdAt: readString(fields.created_at) || readTimestamp(fields.created_at) || doc.createTime || "",
    updatedAt: readString(fields.updated_at) || readTimestamp(fields.updated_at) || doc.updateTime || "",
    reviewedAt: readString(fields.reviewed_at) || readTimestamp(fields.reviewed_at),
    reviewedBy: readString(fields.reviewed_by),
    reviewNote: readString(fields.review_note),
  };
}

function reviewActionFromDocument(doc: FirestoreDocument): ReviewActionLog {
  const fields = doc.fields || {};
  const fallbackId = doc.name.split("/").pop() || "";
  return {
    actionId: readString(fields.action_id) || fallbackId,
    actorId: readString(fields.actor_id),
    actorType: readString(fields.actor_type),
    source: readString(fields.source),
    targetId: readString(fields.target_id),
    previousStatus: readString(fields.previous_status),
    newStatus: readString(fields.new_status),
    reason: readString(fields.reason),
    note: readString(fields.note),
    createdAt: readString(fields.created_at) || readTimestamp(fields.created_at) || doc.createTime || "",
  };
}

function sortReviewItems(items: ReviewItem[]): ReviewItem[] {
  const rank: Record<string, number> = { urgent: 0, high: 1, normal: 2, low: 3 };
  return [...items].sort((a, b) => {
    const priorityDiff = (rank[a.priority] ?? 9) - (rank[b.priority] ?? 9);
    if (priorityDiff !== 0) {
      return priorityDiff;
    }
    return (a.createdAt || a.updatedAt || a.reviewId).localeCompare(
      b.createdAt || b.updatedAt || b.reviewId,
    );
  });
}

function statusForAction(action: ReviewAction): string {
  switch (action) {
    case "approve":
      return "approved";
    case "reject":
      return "rejected";
    case "needs_content":
      return "needs_content";
    case "close":
      return "closed";
    case "reopen":
      return "open";
    default:
      throw new Error(`Unsupported review action: ${action}`);
  }
}

async function listCollection(collection: string): Promise<FirestoreDocument[]> {
  const token = await accessToken();
  const response = await fetch(`${baseUrl()}/${collection}?pageSize=300`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
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
      headers: {
        ...authHeaders(token),
        "content-type": "application/json",
      },
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
    headers: {
      ...authHeaders(token),
      "content-type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });
  if (!response.ok) {
    throw new Error(`Firestore create failed: ${response.status} ${await response.text()}`);
  }
}

function baseUrl(): string {
  const encodedDatabase = encodeURIComponent(DATABASE);
  return `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/${encodedDatabase}/documents`;
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

  try {
    const { stdout } = await execFileAsync(
      "gcloud",
      ["auth", "application-default", "print-access-token"],
      { timeout: TOKEN_TIMEOUT_MS },
    );
    return cacheToken(stdout.trim());
  } catch (error) {
    if (!isSpawnMissing(error)) {
      throw error;
    }
  }

  const localAppData = process.env.LOCALAPPDATA;
  if (!localAppData) {
    throw new Error("gcloud was not found and LOCALAPPDATA is not set");
  }

  const gcloudPs1 = `${localAppData}\\Google\\Cloud SDK\\google-cloud-sdk\\bin\\gcloud.ps1`;
  const { stdout } = await execFileAsync(
    "powershell.exe",
    [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-Command",
      `& '${gcloudPs1}' auth application-default print-access-token`,
    ],
    { timeout: TOKEN_TIMEOUT_MS },
  );
  return cacheToken(stdout.trim());
}

function isSpawnMissing(error: unknown): boolean {
  return Boolean(
    error &&
      typeof error === "object" &&
      "code" in error &&
      (error as { code?: string }).code === "ENOENT",
  );
}

function cacheToken(token: string): string {
  cachedLocalToken = {
    token,
    expiresAt: Date.now() + 45 * 60 * 1000,
  };
  return token;
}

function readString(value: FirestoreValue | undefined): string {
  if (!value) {
    return "";
  }
  if ("stringValue" in value) {
    return value.stringValue;
  }
  if ("timestampValue" in value) {
    return value.timestampValue;
  }
  if ("integerValue" in value) {
    return value.integerValue;
  }
  if ("booleanValue" in value) {
    return String(value.booleanValue);
  }
  return "";
}

function readTimestamp(value: FirestoreValue | undefined): string {
  return value && "timestampValue" in value ? value.timestampValue : "";
}

function readInteger(value: FirestoreValue | undefined): number | null {
  if (!value) {
    return null;
  }
  if ("integerValue" in value) {
    return Number.parseInt(value.integerValue, 10);
  }
  if ("stringValue" in value) {
    const parsed = Number.parseInt(value.stringValue, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }
  return null;
}

function stringValue(value: string): FirestoreValue {
  return { stringValue: value };
}

function timestampValue(value: string): FirestoreValue {
  return { timestampValue: value };
}
