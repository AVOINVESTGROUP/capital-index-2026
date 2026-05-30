import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { RagEngineState, RagFile } from "./types";

const execFileAsync = promisify(execFile);

const PROJECT_ID = process.env.GCP_PROJECT_ID || "capital-index-2026";
const LOCATION = process.env.RAG_ENGINE_LOCATION || "us-central1";
const CORPUS_ID = process.env.RAG_ENGINE_CORPUS_ID || "6241865938233196544";
const CORPUS_DISPLAY_NAME = process.env.RAG_ENGINE_CORPUS_DISPLAY_NAME || "second-brain-vault";
const PROMPT_NAME = process.env.RAG_ENGINE_PROMPT_NAME || "second-brain-vault-base";
const DRIVE_SOURCE = process.env.RAG_ENGINE_DRIVE_SOURCE || "Google Drive / 00-Vault";
const TOKEN_TIMEOUT_MS = 15_000;

let cachedLocalToken: { token: string; expiresAt: number } | null = null;

type GoogleRagCorpus = {
  name?: string;
  displayName?: string;
};

type GoogleRagFile = {
  name?: string;
  displayName?: string;
  createTime?: string;
  updateTime?: string;
};

type GoogleListRagFilesResponse = {
  ragFiles?: GoogleRagFile[];
};

export async function getRagEngineState(): Promise<RagEngineState> {
  const generatedAt = new Date().toISOString();

  if (!PROJECT_ID || !LOCATION || !CORPUS_ID) {
    return {
      generatedAt,
      projectId: PROJECT_ID,
      location: LOCATION,
      corpusId: CORPUS_ID,
      corpusName: "",
      displayName: CORPUS_DISPLAY_NAME,
      promptName: PROMPT_NAME,
      driveSource: DRIVE_SOURCE,
      agentStudioUrl: "",
      ragConsoleUrl: "",
      fileCount: 0,
      files: [],
      status: "not_configured",
      error: "RAG corpus is not configured.",
    };
  }

  try {
    const token = await accessToken();
    const corpusName = `projects/${PROJECT_ID}/locations/${LOCATION}/ragCorpora/${CORPUS_ID}`;
    const [corpus, files] = await Promise.all([
      getCorpus(token, corpusName),
      listRagFiles(token, corpusName),
    ]);

    return {
      generatedAt,
      projectId: PROJECT_ID,
      location: LOCATION,
      corpusId: CORPUS_ID,
      corpusName,
      displayName: corpus.displayName || CORPUS_DISPLAY_NAME,
      promptName: PROMPT_NAME,
      driveSource: DRIVE_SOURCE,
      agentStudioUrl:
        `https://console.cloud.google.com/agent-platform/studio/multimodal` +
        `?project=${encodeURIComponent(PROJECT_ID)}` +
        `&ragCorpusName=${encodeURIComponent(corpusName)}`,
      ragConsoleUrl:
        `https://console.cloud.google.com/agent-platform/rag/locations/${LOCATION}` +
        `/corpus/${CORPUS_ID}/data?project=${encodeURIComponent(PROJECT_ID)}`,
      fileCount: files.length,
      files,
      status: "ready",
    };
  } catch (error) {
    return {
      generatedAt,
      projectId: PROJECT_ID,
      location: LOCATION,
      corpusId: CORPUS_ID,
      corpusName: `projects/${PROJECT_ID}/locations/${LOCATION}/ragCorpora/${CORPUS_ID}`,
      displayName: CORPUS_DISPLAY_NAME,
      promptName: PROMPT_NAME,
      driveSource: DRIVE_SOURCE,
      agentStudioUrl: "",
      ragConsoleUrl: "",
      fileCount: 0,
      files: [],
      status: "error",
      error: error instanceof Error ? error.message : "Unknown RAG Engine error",
    };
  }
}

async function getCorpus(token: string, corpusName: string): Promise<GoogleRagCorpus> {
  const response = await fetch(`${baseUrl()}/${corpusName}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`RAG corpus get failed: ${response.status} ${await response.text()}`);
  }
  return (await response.json()) as GoogleRagCorpus;
}

async function listRagFiles(token: string, corpusName: string): Promise<RagFile[]> {
  const response = await fetch(`${baseUrl()}/${corpusName}/ragFiles?pageSize=1000`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`RAG files list failed: ${response.status} ${await response.text()}`);
  }
  const data = (await response.json()) as GoogleListRagFilesResponse;
  return (data.ragFiles || []).map((file) => ({
    name: file.name || "",
    displayName: file.displayName || file.name?.split("/").pop() || "",
    createTime: file.createTime || "",
    updateTime: file.updateTime || "",
  }));
}

function baseUrl(): string {
  return `https://${LOCATION}-aiplatform.googleapis.com/v1`;
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
