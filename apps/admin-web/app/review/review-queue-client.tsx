"use client";

import { useEffect, useMemo, useState } from "react";
import type { User } from "firebase/auth";
import {
  adminAuth,
  authHeader,
  observeAdminAuth,
  signInWithGoogle,
  signOutAdmin,
} from "@/lib/auth/firebaseClient";
import type {
  ReviewAction,
  ReviewActionLog,
  ReviewActionsResponse,
  ReviewItem,
  ReviewListResponse,
} from "@/lib/reviewQueue/types";
import CleanupQueuePanel from "./cleanup-queue-panel";
import KnowledgePanel from "./knowledge-panel";
import ProgressDashboard from "./progress-dashboard";
import styles from "./review.module.css";
import SourceFilesPanel from "./source-files-panel";

const FILTERS = ["open", "approved", "rejected", "needs_content", "closed", "all"];

const ACTIONS: Array<{
  action: ReviewAction;
  label: string;
  tone: "primary" | "warning" | "danger" | "neutral";
}> = [
  { action: "approve", label: "Approve", tone: "primary" },
  { action: "needs_content", label: "Needs content", tone: "warning" },
  { action: "reject", label: "Reject", tone: "danger" },
  { action: "close", label: "Close", tone: "neutral" },
  { action: "reopen", label: "Reopen", tone: "neutral" },
];

const ACTION_COPY: Record<ReviewAction, { title: string; status: string; detail: string }> = {
  approve: {
    title: "Approve review item",
    status: "approved",
    detail: "Mark this item as approved and record your decision in the audit trail.",
  },
  reject: {
    title: "Reject review item",
    status: "rejected",
    detail: "Mark this item as rejected and record your decision in the audit trail.",
  },
  needs_content: {
    title: "Request more content",
    status: "needs_content",
    detail: "Send this item back for more content or clarification.",
  },
  close: {
    title: "Close review item",
    status: "closed",
    detail: "Close this item without approving or rejecting it.",
  },
  reopen: {
    title: "Reopen review item",
    status: "open",
    detail: "Move this item back to the open queue.",
  },
};

export default function ReviewQueueClient() {
  const [queueMode, setQueueMode] = useState<"review" | "cleanup" | "sources" | "knowledge">("knowledge");
  const [filter, setFilter] = useState("open");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingAction, setSavingAction] = useState<ReviewAction | "">("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  const [authReady, setAuthReady] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [actions, setActions] = useState<ReviewActionLog[]>([]);
  const [actionsLoading, setActionsLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<ReviewAction | "">("");

  const selected = useMemo(
    () => items.find((item) => item.reviewId === selectedId) || items[0],
    [items, selectedId],
  );

  useEffect(() => {
    let unsubscribe = () => {};
    void adminAuth()
      .then((auth) => {
        unsubscribe = observeAdminAuth(auth, (currentUser) => {
          setUser(currentUser);
          setAuthReady(true);
        });
        setAuthReady(true);
      })
      .catch((authError) => {
        setAuthReady(true);
        setError(authError instanceof Error ? authError.message : "Failed to initialize auth");
      });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (user) {
      void loadItems(filter, user);
    }
  }, [filter, user]);

  useEffect(() => {
    if (user && selected?.reviewId) {
      void loadActions(selected.reviewId, user);
    } else {
      setActions([]);
    }
  }, [selected?.reviewId, user]);

  async function loadItems(status: string, currentUser = user) {
    if (!currentUser) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/review-items?status=${status}&limit=100`, {
        headers: await authHeader(currentUser),
        cache: "no-store",
      });
      const payload = (await response.json()) as ReviewListResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load review queue");
      }
      const data = payload as ReviewListResponse;
      setItems(data.items);
      setSelectedId((current) =>
        data.items.some((item) => item.reviewId === current)
          ? current
          : data.items[0]?.reviewId || "",
      );
      setLastUpdated(data.generatedAt);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load review queue");
    } finally {
      setLoading(false);
    }
  }

  async function loadActions(reviewId: string, currentUser = user) {
    if (!currentUser) {
      return;
    }
    setActionsLoading(true);
    try {
      const response = await fetch(`/api/review-items/${reviewId}/actions`, {
        headers: await authHeader(currentUser),
        cache: "no-store",
      });
      const payload = (await response.json()) as ReviewActionsResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load action history");
      }
      setActions((payload as ReviewActionsResponse).actions);
    } catch (historyError) {
      setError(historyError instanceof Error ? historyError.message : "Failed to load action history");
    } finally {
      setActionsLoading(false);
    }
  }

  async function runAction(action: ReviewAction) {
    if (!selected || !user) {
      return;
    }
    setSavingAction(action);
    setError("");
    try {
      const response = await fetch(`/api/review-items/${selected.reviewId}/action`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(await authHeader(user)),
        },
        body: JSON.stringify({ action, note }),
      });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) {
        throw new Error(payload.error || "Failed to update review item");
      }
      setNote("");
      setPendingAction("");
      await loadItems(filter, user);
      await loadActions(selected.reviewId, user);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to update review item");
    } finally {
      setSavingAction("");
    }
  }

  async function signIn() {
    setError("");
    try {
      await signInWithGoogle();
    } catch (signInError) {
      setError(signInError instanceof Error ? signInError.message : "Failed to sign in");
    }
  }

  async function signOut() {
    setItems([]);
    setSelectedId("");
    await signOutAdmin();
  }

  if (!authReady) {
    return (
      <main className={styles.shell}>
        <div className={styles.authPanel}>Loading secure session...</div>
      </main>
    );
  }

  if (!user) {
    return (
      <main className={styles.shell}>
        <section className={styles.authPanel}>
          <p className={styles.eyebrow}>CAPITAL INDEX Admin</p>
          <h1>Admin Queue</h1>
          <p>Sign in with an approved Google account.</p>
          <button className={styles.primary} onClick={signIn} type="button">
            Sign in with Google
          </button>
          {error ? <div className={styles.error}>{error}</div> : null}
        </section>
      </main>
    );
  }

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>CAPITAL INDEX Admin</p>
          <h1>{titleForMode(queueMode)}</h1>
        </div>
        <div className={styles.headerStats}>
          <span>{user.email}</span>
          <span>{queueMode}</span>
          <span>{lastUpdated && queueMode === "review" ? formatDate(lastUpdated) : "Live data"}</span>
          <button className={styles.signOutButton} onClick={signOut} type="button">
            Sign out
          </button>
        </div>
      </header>

      <nav className={styles.modeTabs} aria-label="Admin queue mode">
        <button
          className={queueMode === "review" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setQueueMode("review")}
          type="button"
        >
          Review Queue
        </button>
        <button
          className={queueMode === "cleanup" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setQueueMode("cleanup")}
          type="button"
        >
          Cleanup Queue
        </button>
        <button
          className={queueMode === "sources" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setQueueMode("sources")}
          type="button"
        >
          Source Files
        </button>
        <button
          className={queueMode === "knowledge" ? styles.modeTabActive : styles.modeTab}
          onClick={() => setQueueMode("knowledge")}
          type="button"
        >
          Knowledge
        </button>
      </nav>

      <ProgressDashboard user={user} />

      {queueMode === "cleanup" ? <CleanupQueuePanel user={user} /> : null}
      {queueMode === "sources" ? <SourceFilesPanel user={user} /> : null}
      {queueMode === "knowledge" ? <KnowledgePanel user={user} /> : null}

      {queueMode === "review" ? (
        <>
      <section className={styles.toolbar} aria-label="Review filters">
        <div className={styles.segmented}>
          {FILTERS.map((status) => (
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

      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.workspace}>
        <div className={styles.listPane}>
          <div className={styles.listHeader}>
            <span>Priority</span>
            <span>Reason</span>
            <span>Status</span>
          </div>
          {loading ? <div className={styles.empty}>Loading review items...</div> : null}
          {!loading && items.length === 0 ? (
            <div className={styles.empty}>No review items for this filter.</div>
          ) : null}
          {items.map((item) => (
            <button
              key={item.reviewId}
              className={
                selected?.reviewId === item.reviewId ? styles.rowSelected : styles.rowButton
              }
              onClick={() => setSelectedId(item.reviewId)}
              type="button"
            >
              <span className={styles.priority}>{item.priority}</span>
              <span>
                <strong>{item.reason}</strong>
                <small>{item.docTitle || "(untitled)"}</small>
              </span>
              <StatusPill status={item.status} />
            </button>
          ))}
        </div>

        <aside className={styles.detailPane}>
          {selected ? (
            <>
              <div className={styles.detailTop}>
                <div>
                  <p className={styles.eyebrow}>Selected item</p>
                  <h2>{selected.docTitle || "(untitled)"}</h2>
                </div>
                <StatusPill status={selected.status} />
              </div>

              <dl className={styles.metaGrid}>
                <Field label="Review ID" value={selected.reviewId} />
                <Field label="Reason" value={selected.reason} />
                <Field label="File ID" value={selected.fileId} />
                <Field label="Sensitivity" value={selected.sensitivityClass} />
                <Field label="Source" value={`${selected.source} / ${selected.sourceCollection}`} />
                <Field label="Decision" value={selected.sourceDecisionId} />
                <Field label="Trace" value={selected.traceId} />
                <Field label="Next action" value={selected.nextAction} />
                <Field label="Characters" value={selected.charCount?.toString() || "0"} />
                <Field label="Updated" value={formatDate(selected.updatedAt)} />
                <Field label="Reviewed by" value={selected.reviewedBy || "-"} />
                <Field label="Reviewed at" value={formatDate(selected.reviewedAt || "")} />
              </dl>

              <label className={styles.noteLabel} htmlFor="review-note">
                Review note
              </label>
              <textarea
                id="review-note"
                className={styles.note}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Add context for audit trail"
                rows={4}
              />

              <div className={styles.actions}>
                {ACTIONS.map((item) => (
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
                  <p className={styles.eyebrow}>Confirm decision</p>
                  <h3>{ACTION_COPY[pendingAction].title}</h3>
                  <p>{ACTION_COPY[pendingAction].detail}</p>
                  <dl className={styles.confirmGrid}>
                    <Field label="Current status" value={selected.status} />
                    <Field label="New status" value={ACTION_COPY[pendingAction].status} />
                    <Field label="Actor" value={user.email || "-"} />
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

              <section className={styles.auditTrail}>
                <div className={styles.sectionTop}>
                  <div>
                    <p className={styles.eyebrow}>Audit trail</p>
                    <h3>Review actions</h3>
                  </div>
                  <button
                    className={styles.neutral}
                    disabled={actionsLoading}
                    onClick={() => loadActions(selected.reviewId)}
                    type="button"
                  >
                    {actionsLoading ? "Loading..." : "Reload"}
                  </button>
                </div>
                {actionsLoading ? <div className={styles.emptyInline}>Loading action history...</div> : null}
                {!actionsLoading && actions.length === 0 ? (
                  <div className={styles.emptyInline}>No actions recorded yet.</div>
                ) : null}
                {actions.map((action) => (
                  <article className={styles.auditItem} key={action.actionId}>
                    <div>
                      <strong>{action.reason}</strong>
                      <span>
                        {action.previousStatus || "-"} to {action.newStatus || "-"}
                      </span>
                    </div>
                    <small>
                      {formatDate(action.createdAt)} by {action.actorId || "-"}
                    </small>
                    {action.note ? <p>{action.note}</p> : null}
                  </article>
                ))}
              </section>
            </>
          ) : (
            <div className={styles.empty}>Select a review item.</div>
          )}
        </aside>
      </section>
        </>
      ) : null}
    </main>
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

function titleForMode(mode: "review" | "cleanup" | "sources" | "knowledge") {
  switch (mode) {
    case "cleanup":
      return "Cleanup Queue";
    case "sources":
      return "Source Files";
    case "knowledge":
      return "Knowledge";
    case "review":
    default:
      return "Review Queue";
  }
}
