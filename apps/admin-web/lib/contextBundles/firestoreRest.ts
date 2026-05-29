import { execFile } from "node:child_process";
import { randomUUID } from "node:crypto";
import { promisify } from "node:util";
import type { ContextBundle, ContextBundleAction, ContextBundleStatus } from "./types";

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
const LOCAL_ACTOR = process.env.ADMIN_WEB_LOCAL_ACTOR || "local_operator";
const TOKEN_TIMEOUT_MS = 15_000;

let cachedLocalToken: { token: string; expiresAt: number } | null = null;

export async function listContextBundles(limit: number): Promise<ContextBundle[]> {
  const [bundleDocs, projectionDocs] = await Promise.all([
    listCollection("context_bundles", Math.max(limit + 1, 50)),
    listCollection("vault_projections", 500),
  ]);
  const projectionsByBundleId = new Map<string, FirestoreDocument>();
  projectionDocs.forEach((doc) => {
    const fields = doc.fields || {};
    const bundleId = readString(fields.bundle_id);
    const projectionId = doc.name.split("/").pop() || "";
    if (bundleId && projectionId !== "current_second_brain" && !projectionsByBundleId.has(bundleId)) {
      projectionsByBundleId.set(bundleId, doc);
    }
  });

  return bundleDocs
    .filter((doc) => doc.name.split("/").pop() !== "current")
    .map((doc) => contextBundleFromDocument(doc, projectionsByBundleId))
    .sort((a, b) => (b.createdAt || "").localeCompare(a.createdAt || ""))
    .slice(0, limit);
}

export async function updateContextBundle(
  bundleId: string,
  action: ContextBundleAction,
  note: string,
  actorId: string | undefined,
): Promise<{
  actionId: string;
  previousStatus: string;
  newStatus: ContextBundleStatus;
}> {
  const existing = await getDocument("context_bundles", bundleId);
  if (!existing) {
    throw new Error(`Context bundle not found: ${bundleId}`);
  }
  const bundle = contextBundleFromDocument(existing, new Map());
  const now = new Date().toISOString();
  const resolvedActor = actorId?.trim() || LOCAL_ACTOR;
  const newStatus = statusForAction(action);

  await patchDocument(
    "context_bundles",
    bundleId,
    {
      approval_status: stringValue(newStatus),
      approved_at: action === "approve" ? timestampValue(now) : nullValue(),
      approved_by: action === "approve" ? stringValue(resolvedActor) : nullValue(),
      review_note: stringValue(note.trim()),
      reviewed_at: timestampValue(now),
      reviewed_by: stringValue(resolvedActor),
    },
    ["approval_status", "approved_at", "approved_by", "review_note", "reviewed_at", "reviewed_by"],
  );

  if (bundleId !== "current") {
    await patchDocument(
      "context_bundles",
      "current",
      {
        approval_status: stringValue(newStatus),
        approved_at: action === "approve" ? timestampValue(now) : nullValue(),
        approved_by: action === "approve" ? stringValue(resolvedActor) : nullValue(),
        review_note: stringValue(note.trim()),
        reviewed_at: timestampValue(now),
        reviewed_by: stringValue(resolvedActor),
      },
      ["approval_status", "approved_at", "approved_by", "review_note", "reviewed_at", "reviewed_by"],
    ).catch(() => undefined);
  }

  const actionId = `context_bundle_action_${randomUUID().replace(/-/g, "").slice(0, 24)}`;
  await createDocument("context_bundle_actions", actionId, {
    schema_version: stringValue("capital.context_bundle_action.v1"),
    action_id: stringValue(actionId),
    bundle_id: stringValue(bundleId),
    actor_id: stringValue(resolvedActor),
    actor_type: stringValue("human_operator"),
    action: stringValue(action),
    previous_status: stringValue(bundle.approvalStatus),
    new_status: stringValue(newStatus),
    note: stringValue(note.trim()),
    created_at: timestampValue(now),
  });

  return {
    actionId,
    previousStatus: bundle.approvalStatus,
    newStatus,
  };
}

function contextBundleFromDocument(
  doc: FirestoreDocument,
  projectionsByBundleId: Map<string, FirestoreDocument>,
): ContextBundle {
  const fields = doc.fields || {};
  const bundleId = readString(fields.bundle_id) || doc.name.split("/").pop() || "";
  const body = readMap(fields.body);
  const projectionFields = projectionsByBundleId.get(bundleId)?.fields || {};
  const recentClaims = readArray(body.recent_claims).map(claimFromValue);
  const relationships = readArray(body.relationship_graph).map(relationshipFromValue);
  const sourceFileIds = readArray(fields.source_file_ids).map(readString).filter(Boolean);
  const claimIds = readArray(body.claim_ids).map(readString).filter(Boolean);
  const entityIds = readArray(body.entity_ids).map(readString).filter(Boolean);
  const relationshipIds = readArray(body.relationship_ids).map(readString).filter(Boolean);
  const evidenceIds = readArray(body.evidence_ids).map(readString).filter(Boolean);

  return {
    bundleId,
    bundleType: readString(fields.bundle_type),
    approvalStatus: readString(fields.approval_status) || "draft",
    requiresHumanApproval: readBoolean(fields.requires_human_approval),
    createdAt: readString(fields.created_at) || readTimestamp(fields.created_at),
    createdBy: readString(fields.created_by),
    approvedAt: readString(fields.approved_at) || readTimestamp(fields.approved_at),
    approvedBy: readString(fields.approved_by),
    sourceFileCount: sourceFileIds.length,
    claimCount: claimIds.length,
    entityCount: entityIds.length,
    relationshipCount: relationshipIds.length,
    evidenceCount: evidenceIds.length,
    actualBundleBytes: readNumber(fields.actual_bundle_bytes),
    maxBundleBytes: readNumber(fields.max_bundle_bytes),
    sourceFileIds,
    omittedCount: readArray(fields.omitted_or_blocked_sources).length,
    recentClaims,
    relationships,
    vaultProjection: projectionFields.projection_id
      ? {
          projectionId: readString(projectionFields.projection_id),
          path: readString(projectionFields.path),
          title: readString(projectionFields.title),
          content: readString(projectionFields.content),
          writeStatus: readString(projectionFields.write_status),
          requiresApproval: readBoolean(projectionFields.requires_approval),
        }
      : undefined,
  };
}

function claimFromValue(value: FirestoreValue) {
  const fields = readMap(value);
  return {
    claimId: readString(fields.claim_id),
    claimType: readString(fields.claim_type),
    text: readString(fields.text),
    confidence: readNumber(fields.confidence),
    evidenceIds: readArray(fields.evidence_ids).map(readString).filter(Boolean),
    sourceFileIds: readArray(fields.source_file_ids).map(readString).filter(Boolean),
  };
}

function relationshipFromValue(value: FirestoreValue) {
  const fields = readMap(value);
  return {
    relationshipId: readString(fields.relationship_id),
    relationshipType: readString(fields.relationship_type),
    fromId: readString(fields.from_id),
    toId: readString(fields.to_id),
    confidence: readNumber(fields.confidence),
    evidenceIds: readArray(fields.evidence_ids).map(readString).filter(Boolean),
  };
}

function statusForAction(action: ContextBundleAction): ContextBundleStatus {
  switch (action) {
    case "approve":
      return "approved";
    case "reject":
      return "rejected";
    case "supersede":
    default:
      return "superseded";
  }
}

async function listCollection(collection: string, pageSize: number): Promise<FirestoreDocument[]> {
  const token = await accessToken();
  const documents: FirestoreDocument[] = [];
  let pageToken = "";
  do {
    const params = new URLSearchParams({ pageSize: String(Math.min(pageSize, 1000)) });
    if (pageToken) params.set("pageToken", pageToken);
    const response = await fetch(`${baseUrl()}/${collection}?${params.toString()}`, {
      headers: authHeaders(token),
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

function readMap(value: FirestoreValue | undefined): Record<string, FirestoreValue> {
  return value && "mapValue" in value ? value.mapValue.fields || {} : {};
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

function readTimestamp(value: FirestoreValue | undefined): string {
  return value && "timestampValue" in value ? value.timestampValue : "";
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

function stringValue(value: string): FirestoreValue {
  return { stringValue: value };
}

function timestampValue(value: string): FirestoreValue {
  return { timestampValue: value };
}

function nullValue(): FirestoreValue {
  return { nullValue: null };
}
