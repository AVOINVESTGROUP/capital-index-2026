"use client";

import { useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type { VaultProjectionState } from "@/lib/contextBundles/types";
import styles from "./review.module.css";

export default function VaultPanel({ user }: { user: User }) {
  const [state, setState] = useState<VaultProjectionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void loadState();
  }, []);

  async function loadState() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/vault-projections", {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as VaultProjectionState | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load vault projection");
      }
      setState(payload as VaultProjectionState);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load vault projection");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className={styles.toolbar} aria-label="Vault projection actions">
        <div className={styles.headerStatsInline}>
          <span>{state?.status || "loading"}</span>
          <span>{state?.approvedMemory ? "approved memory ready" : "no approved memory"}</span>
          <span>{state?.projection ? state.projection.writeStatus : "no projection"}</span>
          <span>{state?.generatedAt ? formatDate(state.generatedAt) : "Not loaded"}</span>
        </div>
        <button className={styles.refreshButton} onClick={loadState} type="button">
          Refresh
        </button>
      </section>

      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.workspace}>
        <div className={styles.listPane}>
          <div className={styles.listHeader}>
            <span>Status</span>
            <span>Vault item</span>
            <span>Action</span>
          </div>
          {loading ? <div className={styles.empty}>Loading vault projection...</div> : null}
          {!loading && state?.status === "no_approved_memory" ? (
            <div className={styles.empty}>Approve a context bundle before publishing Vault memory.</div>
          ) : null}
          {!loading && state?.approvedMemory ? (
            <button className={styles.rowSelected} type="button">
              <span className={styles.priority}>{state.status}</span>
              <span>
                <strong>{state.projection?.path || "00_SECOND_BRAIN_INDEX.md"}</strong>
                <small>{state.approvedMemory.bundleId}</small>
              </span>
              <StatusPill status={state.projection?.writeStatus || "preview"} />
            </button>
          ) : null}
        </div>

        <aside className={styles.detailPane}>
          {state?.approvedMemory ? (
            <>
              <div className={styles.detailTop}>
                <div>
                  <p className={styles.eyebrow}>Vault projection</p>
                  <h2>{state.projection?.title || "CAPITAL INDEX Second Brain"}</h2>
                </div>
                <StatusPill status={state.status} />
              </div>

              <dl className={styles.metaGrid}>
                <Field label="Approved bundle" value={state.approvedMemory.bundleId} />
                <Field label="Approved at" value={formatDate(state.approvedMemory.approvedAt)} />
                <Field label="Approved by" value={state.approvedMemory.approvedBy || "-"} />
                <Field label="Target path" value={state.projection?.path || "00_SECOND_BRAIN_INDEX.md"} />
                <Field label="Source files" value={String(state.approvedMemory.sourceFileCount)} />
                <Field label="Evidence" value={String(state.approvedMemory.evidenceCount)} />
                <Field label="Claims" value={String(state.approvedMemory.claimCount)} />
                <Field label="Relationships" value={String(state.approvedMemory.relationshipCount)} />
                <Field label="AI reading" value={state.approvedMemory.aiReadingStatus || "-"} />
                <Field label="Write status" value={state.projection?.writeStatus || "preview"} />
              </dl>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>What will go to Obsidian</p>
                <article className={styles.auditItem}>
                  <div>
                    <strong>Human summary</strong>
                    <span>{state.approvedMemory.aiExecutiveSummary || "-"}</span>
                  </div>
                </article>
              </section>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>Markdown preview</p>
                <pre>{state.projection?.content || "Projection is missing or stale for this approved bundle."}</pre>
              </section>
            </>
          ) : (
            <div className={styles.empty}>No approved memory yet. Approve a context bundle first.</div>
          )}
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
