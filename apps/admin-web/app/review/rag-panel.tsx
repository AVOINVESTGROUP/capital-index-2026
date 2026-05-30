"use client";

import { useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type { RagEngineState } from "@/lib/ragEngine/types";
import styles from "./review.module.css";

export default function RagPanel({ user }: { user: User }) {
  const [state, setState] = useState<RagEngineState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadState();
  }, []);

  async function loadState() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/rag-engine", {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as RagEngineState | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load RAG Engine state");
      }
      setState(payload as RagEngineState);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load RAG Engine state");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className={styles.toolbar} aria-label="RAG Engine actions">
        <div className={styles.headerStatsInline}>
          <span>{state?.displayName || "second-brain-vault"}</span>
          <span>{state?.status || "loading"}</span>
          <span>{state ? `${state.fileCount} imported files` : "files loading"}</span>
          <span>{state?.generatedAt ? formatDate(state.generatedAt) : "Not loaded"}</span>
        </div>
        <button className={styles.refreshButton} onClick={loadState} type="button">
          Refresh
        </button>
      </section>

      {error ? <div className={styles.error}>{error}</div> : null}
      {state?.error ? <div className={styles.error}>{state.error}</div> : null}

      <section className={styles.workspace}>
        <div className={styles.listPane}>
          <div className={styles.listHeader}>
            <span>Status</span>
            <span>RAG file</span>
            <span>Imported</span>
          </div>
          {loading ? <div className={styles.empty}>Loading RAG corpus...</div> : null}
          {!loading && !state?.files.length ? (
            <div className={styles.empty}>No RAG files visible for this corpus.</div>
          ) : null}
          {state?.files.map((file) => (
            <div className={styles.rowButton} key={file.name || file.displayName}>
              <span className={styles.priority}>Imported</span>
              <span>
                <strong>{file.displayName || "(unnamed)"}</strong>
                <small>{file.name}</small>
              </span>
              <StatusPill status="active" />
            </div>
          ))}
        </div>

        <aside className={styles.detailPane}>
          <div className={styles.detailTop}>
            <div>
              <p className={styles.eyebrow}>Vertex RAG corpus</p>
              <h2>{state?.displayName || "second-brain-vault"}</h2>
            </div>
            <StatusPill status={state?.status || "loading"} />
          </div>

          <dl className={styles.metaGrid}>
            <Field label="Project" value={state?.projectId || "-"} />
            <Field label="Region" value={state?.location || "-"} />
            <Field label="Corpus ID" value={state?.corpusId || "-"} />
            <Field label="Prompt" value={state?.promptName || "second-brain-vault-base"} />
            <Field label="Drive source" value={state?.driveSource || "Google Drive / 00-Vault"} />
            <Field label="Imported files" value={state ? String(state.fileCount) : "-"} />
          </dl>

          <section className={styles.knowledgeBlock}>
            <p className={styles.eyebrow}>Control rules</p>
            <article className={styles.auditItem}>
              <p>
                RAG is the knowledge plane. Admin Web is the control plane. The assistant may
                answer from this corpus, but permanent memory and Obsidian changes still require
                human approval.
              </p>
            </article>
          </section>

          <section className={styles.actions}>
            {state?.agentStudioUrl ? (
              <a className={styles.openLink} href={state.agentStudioUrl} rel="noreferrer" target="_blank">
                Test in Agent Studio
              </a>
            ) : null}
            {state?.ragConsoleUrl ? (
              <a className={styles.openLink} href={state.ragConsoleUrl} rel="noreferrer" target="_blank">
                Open RAG corpus
              </a>
            ) : null}
          </section>

          <section className={styles.knowledgeBlock}>
            <p className={styles.eyebrow}>System instructions</p>
            <pre>{SYSTEM_INSTRUCTIONS_PREVIEW}</pre>
          </section>
        </aside>
      </section>
    </>
  );
}

function StatusPill({ status }: { status: string }) {
  return <span className={`${styles.status} ${styles[`status_${status}`] || ""}`}>{status}</span>;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value || "-"}</dd>
    </div>
  );
}

function formatDate(value: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

const SYSTEM_INSTRUCTIONS_PREVIEW = `Use the connected Vertex RAG corpus first.
Separate facts, inferences, hypotheses, and next actions.
Do not invent unsupported facts.
Mention source files for important claims.
Propose Obsidian updates only as drafts for human approval.`;
