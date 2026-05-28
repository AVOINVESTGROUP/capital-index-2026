"use client";

import { useEffect, useMemo, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type {
  SourceFile,
  SourceFileAction,
  SourceFilesListResponse,
} from "@/lib/sourceFiles/types";
import styles from "./review.module.css";

const SOURCE_FILTERS = [
  "needs_human_review",
  "active",
  "do_not_index",
  "candidate_empty",
  "candidate_duplicate",
  "candidate_stale",
  "candidate_archive",
  "all",
];

const SOURCE_ACTIONS: Array<{
  action: SourceFileAction;
  label: string;
  tone: "primary" | "warning" | "danger";
}> = [
  { action: "activate", label: "Approve source", tone: "primary" },
  { action: "needs_review", label: "Needs review", tone: "warning" },
  { action: "do_not_index", label: "Do not index", tone: "danger" },
];

const ACTION_COPY: Record<SourceFileAction, { title: string; detail: string; sourceStatus: string }> = {
  activate: {
    title: "Approve file as source",
    sourceStatus: "active",
    detail: "Allow this file to enter entity extraction, graph building, embeddings, and AI context.",
  },
  needs_review: {
    title: "Keep file in human review",
    sourceStatus: "needs_human_review",
    detail: "Keep this file blocked from downstream AI processing until it is reviewed again.",
  },
  do_not_index: {
    title: "Block file from indexing",
    sourceStatus: "do_not_index",
    detail: "Prevent this file from entering AI context, embeddings, entity extraction, and graph building.",
  },
};

export default function SourceFilesPanel({ user }: { user: User }) {
  const [filter, setFilter] = useState("needs_human_review");
  const [items, setItems] = useState<SourceFile[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingAction, setSavingAction] = useState<SourceFileAction | "">("");
  const [pendingAction, setPendingAction] = useState<SourceFileAction | "">("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const selected = useMemo(
    () => items.find((item) => item.fileId === selectedId) || items[0],
    [items, selectedId],
  );

  useEffect(() => {
    void loadItems(filter);
  }, [filter]);

  async function loadItems(status: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/files?status=${status}&limit=100`, {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as SourceFilesListResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load source files");
      }
      const data = payload as SourceFilesListResponse;
      setItems(data.items);
      setSelectedId((current) =>
        data.items.some((item) => item.fileId === current) ? current : data.items[0]?.fileId || "",
      );
      setLastUpdated(data.generatedAt);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load source files");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: SourceFileAction) {
    if (!selected) {
      return;
    }
    setSavingAction(action);
    setError("");
    try {
      const response = await fetch(`/api/files/${encodeURIComponent(selected.fileId)}/source-quality`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(await authHeader(user)),
        },
        body: JSON.stringify({ action, note }),
      });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) {
        throw new Error(payload.error || "Failed to update source file");
      }
      setNote("");
      setPendingAction("");
      await loadItems(filter);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to update source file");
    } finally {
      setSavingAction("");
    }
  }

  return (
    <>
      <section className={styles.toolbar} aria-label="Source file filters">
        <div className={styles.segmented}>
          {SOURCE_FILTERS.map((status) => (
            <button
              key={status}
              className={filter === status ? styles.segmentActive : styles.segment}
              onClick={() => setFilter(status)}
              type="button"
            >
              {status.replaceAll("_", " ")}
            </button>
          ))}
        </div>
        <button className={styles.refreshButton} onClick={() => loadItems(filter)} type="button">
          Refresh
        </button>
      </section>

      <div className={styles.headerStatsInline}>
        <span>{items.length} files</span>
        <span>{lastUpdated ? formatDate(lastUpdated) : "Not loaded"}</span>
      </div>

      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.workspace}>
        <div className={styles.listPane}>
          <div className={styles.listHeader}>
            <span>Eligible</span>
            <span>File</span>
            <span>Status</span>
          </div>
          {loading ? <div className={styles.empty}>Loading source files...</div> : null}
          {!loading && items.length === 0 ? (
            <div className={styles.empty}>No source files for this filter.</div>
          ) : null}
          {items.map((item) => (
            <button
              key={item.fileId}
              className={selected?.fileId === item.fileId ? styles.rowSelected : styles.rowButton}
              onClick={() => setSelectedId(item.fileId)}
              type="button"
            >
              <span className={styles.priority}>{item.indexEligible ? "Yes" : "No"}</span>
              <span>
                <strong>{item.name || "(untitled)"}</strong>
                <small>{item.mimeType || item.fileId}</small>
              </span>
              <StatusPill status={item.sourceStatus} />
            </button>
          ))}
        </div>

        <aside className={styles.detailPane}>
          {selected ? (
            <>
              <div className={styles.detailTop}>
                <div>
                  <p className={styles.eyebrow}>Source file</p>
                  <h2>{selected.name || "(untitled)"}</h2>
                </div>
                <StatusPill status={selected.sourceStatus} />
              </div>

              {selected.webViewLink ? (
                <a
                  className={styles.openLink}
                  href={selected.webViewLink}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open in Drive
                </a>
              ) : null}

              <dl className={styles.metaGrid}>
                <Field label="File ID" value={selected.fileId} />
                <Field label="MIME type" value={selected.mimeType || "-"} />
                <Field label="Project" value={selected.projectId || "-"} />
                <Field label="Source" value={selected.sourceRegistryId || "-"} />
                <Field label="Source status" value={selected.sourceStatus} />
                <Field label="Index eligible" value={selected.indexEligible ? "true" : "false"} />
                <Field label="Human block" value={selected.humanBlock ? "true" : "false"} />
                <Field label="Metadata" value={selected.metadataStatus || "-"} />
                <Field label="Modified" value={formatDate(selected.modifiedTime)} />
                <Field label="Approved by" value={selected.sourceApprovedBy || "-"} />
                <Field label="Approved at" value={formatDate(selected.sourceApprovedAt)} />
                <Field label="Quality updated" value={formatDate(selected.sourceQualityUpdatedAt)} />
              </dl>

              <label className={styles.noteLabel} htmlFor="source-file-note">
                Source quality note
              </label>
              <textarea
                id="source-file-note"
                className={styles.note}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Add context for source quality audit trail"
                rows={4}
              />

              <div className={styles.actions}>
                {SOURCE_ACTIONS.map((item) => (
                  <button
                    key={item.action}
                    className={styles[item.tone]}
                    disabled={Boolean(savingAction)}
                    onClick={() => setPendingAction(item.action)}
                    type="button"
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {pendingAction ? (
                <section className={styles.confirmPanel}>
                  <p className={styles.eyebrow}>Confirm source decision</p>
                  <h3>{ACTION_COPY[pendingAction].title}</h3>
                  <p>{ACTION_COPY[pendingAction].detail}</p>
                  <dl className={styles.confirmGrid}>
                    <Field label="Current source status" value={selected.sourceStatus} />
                    <Field label="New source status" value={ACTION_COPY[pendingAction].sourceStatus} />
                    <Field label="Drive mutation" value="none" />
                    <Field label="Audit note" value={note.trim() || "(empty)"} />
                  </dl>
                  <div className={styles.confirmActions}>
                    <button
                      className={styles.primary}
                      disabled={Boolean(savingAction)}
                      onClick={() => runAction(pendingAction)}
                      type="button"
                    >
                      {savingAction === pendingAction ? "Saving..." : "Confirm"}
                    </button>
                    <button
                      className={styles.neutral}
                      disabled={Boolean(savingAction)}
                      onClick={() => setPendingAction("")}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </section>
              ) : null}
            </>
          ) : (
            <div className={styles.empty}>Select a source file.</div>
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
