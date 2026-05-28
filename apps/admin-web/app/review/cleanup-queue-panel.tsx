"use client";

import { useEffect, useMemo, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type { CleanupAction, CleanupItem, CleanupListResponse } from "@/lib/cleanupQueue/types";
import styles from "./review.module.css";

const CLEANUP_FILTERS = ["open", "approved", "ignored", "applied", "all"];

const CLEANUP_ACTIONS: Array<{
  action: CleanupAction;
  label: string;
  tone: "primary" | "warning" | "danger" | "neutral";
}> = [
  { action: "keep_active", label: "Keep active", tone: "primary" },
  { action: "mark_duplicate", label: "Mark duplicate", tone: "warning" },
  { action: "archive", label: "Archive candidate", tone: "warning" },
  { action: "move_to_review", label: "Move to review", tone: "neutral" },
  { action: "do_not_index", label: "Do not index", tone: "danger" },
  { action: "ignore", label: "Ignore", tone: "neutral" },
];

const ACTION_COPY: Record<CleanupAction, { title: string; sourceStatus: string; detail: string }> = {
  keep_active: {
    title: "Keep as active source",
    sourceStatus: "active",
    detail: "Mark this file as eligible source material. This does not mutate Drive.",
  },
  mark_duplicate: {
    title: "Mark as duplicate candidate",
    sourceStatus: "candidate_duplicate",
    detail: "Keep the duplicate mark for governance and prevent it from becoming independent evidence.",
  },
  archive: {
    title: "Approve archive candidate",
    sourceStatus: "candidate_archive",
    detail: "Approve the archive recommendation. Actual Drive archive/move is not performed yet.",
  },
  move_to_review: {
    title: "Move recommendation to review",
    sourceStatus: "needs_human_review",
    detail: "Keep this file in human review until project/source mapping is resolved.",
  },
  do_not_index: {
    title: "Mark do not index",
    sourceStatus: "do_not_index",
    detail: "Block this file from AI context, embeddings, and graph extraction.",
  },
  ignore: {
    title: "Ignore recommendation",
    sourceStatus: "(unchanged)",
    detail: "Close the cleanup recommendation without changing the source status.",
  },
};

export default function CleanupQueuePanel({ user }: { user: User }) {
  const [filter, setFilter] = useState("open");
  const [items, setItems] = useState<CleanupItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingAction, setSavingAction] = useState<CleanupAction | "">("");
  const [pendingAction, setPendingAction] = useState<CleanupAction | "">("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const selected = useMemo(
    () => items.find((item) => item.cleanupId === selectedId) || items[0],
    [items, selectedId],
  );

  useEffect(() => {
    void loadItems(filter);
  }, [filter]);

  async function loadItems(status: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/cleanup-items?status=${status}&limit=100`, {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as CleanupListResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load cleanup queue");
      }
      const data = payload as CleanupListResponse;
      setItems(data.items);
      setSelectedId((current) =>
        data.items.some((item) => item.cleanupId === current)
          ? current
          : data.items[0]?.cleanupId || "",
      );
      setLastUpdated(data.generatedAt);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load cleanup queue");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: CleanupAction) {
    if (!selected) {
      return;
    }
    setSavingAction(action);
    setError("");
    try {
      const response = await fetch(`/api/cleanup-items/${selected.cleanupId}/action`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(await authHeader(user)),
        },
        body: JSON.stringify({ action, note }),
      });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) {
        throw new Error(payload.error || "Failed to update cleanup item");
      }
      setNote("");
      setPendingAction("");
      await loadItems(filter);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to update cleanup item");
    } finally {
      setSavingAction("");
    }
  }

  return (
    <>
      <section className={styles.toolbar} aria-label="Cleanup filters">
        <div className={styles.segmented}>
          {CLEANUP_FILTERS.map((status) => (
            <button
              key={status}
              className={filter === status ? styles.segmentActive : styles.segment}
              onClick={() => setFilter(status)}
              type="button"
            >
              {status.replace("_", " ")}
            </button>
          ))}
        </div>
        <button className={styles.refreshButton} onClick={() => loadItems(filter)} type="button">
          Refresh
        </button>
      </section>

      <div className={styles.headerStatsInline}>
        <span>{items.length} items</span>
        <span>{lastUpdated ? formatDate(lastUpdated) : "Not loaded"}</span>
      </div>

      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.workspace}>
        <div className={styles.listPane}>
          <div className={styles.listHeader}>
            <span>Confidence</span>
            <span>Reason</span>
            <span>Status</span>
          </div>
          {loading ? <div className={styles.empty}>Loading cleanup recommendations...</div> : null}
          {!loading && items.length === 0 ? (
            <div className={styles.empty}>No cleanup recommendations for this filter.</div>
          ) : null}
          {items.map((item) => (
            <button
              key={item.cleanupId}
              className={
                selected?.cleanupId === item.cleanupId ? styles.rowSelected : styles.rowButton
              }
              onClick={() => setSelectedId(item.cleanupId)}
              type="button"
            >
              <span className={styles.priority}>{formatConfidence(item.confidence)}</span>
              <span>
                <strong>{item.reason}</strong>
                <small>{item.fileId}</small>
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
                  <p className={styles.eyebrow}>Cleanup recommendation</p>
                  <h2>{selected.reason}</h2>
                </div>
                <StatusPill status={selected.status} />
              </div>

              <dl className={styles.metaGrid}>
                <Field label="Cleanup ID" value={selected.cleanupId} />
                <Field label="File ID" value={selected.fileId} />
                <Field label="Project" value={selected.projectId || "-"} />
                <Field label="Source" value={selected.sourceRegistryId || "-"} />
                <Field label="Source status" value={selected.sourceStatus} />
                <Field label="Recommended" value={selected.recommendedAction} />
                <Field label="Confidence" value={formatConfidence(selected.confidence)} />
                <Field label="Age" value={selected.ageDays === null ? "-" : `${selected.ageDays} days`} />
                <Field label="Modified" value={formatDate(selected.modifiedAt)} />
                <Field label="Size" value={selected.size === null ? "-" : selected.size.toString()} />
                <Field label="Matched files" value={selected.matchedFileIds.join(", ") || "-"} />
                <Field label="Created" value={formatDate(selected.createdAt)} />
              </dl>

              <section className={styles.auditTrail}>
                <p className={styles.eyebrow}>Evidence</p>
                <div className={styles.signalList}>
                  {selected.evidenceSignals.length > 0 ? (
                    selected.evidenceSignals.map((signal) => <span key={signal}>{signal}</span>)
                  ) : (
                    <span>No signals</span>
                  )}
                </div>
              </section>

              <label className={styles.noteLabel} htmlFor="cleanup-note">
                Cleanup note
              </label>
              <textarea
                id="cleanup-note"
                className={styles.note}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Add context for cleanup audit trail"
                rows={4}
              />

              <div className={styles.actions}>
                {CLEANUP_ACTIONS.map((item) => (
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
                  <p className={styles.eyebrow}>Confirm cleanup decision</p>
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
            <div className={styles.empty}>Select a cleanup recommendation.</div>
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

function formatConfidence(value: number | null) {
  if (value === null) {
    return "-";
  }
  return `${Math.round(value * 100)}%`;
}
