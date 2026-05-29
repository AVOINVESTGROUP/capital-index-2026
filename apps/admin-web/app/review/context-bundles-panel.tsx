"use client";

import { useEffect, useMemo, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type {
  ContextBundle,
  ContextBundleAction,
  ContextBundleListResponse,
} from "@/lib/contextBundles/types";
import styles from "./review.module.css";

const ACTIONS: Array<{ action: ContextBundleAction; label: string; tone: "primary" | "warning" | "neutral" }> = [
  { action: "approve", label: "Approve bundle", tone: "primary" },
  { action: "reject", label: "Reject", tone: "warning" },
  { action: "supersede", label: "Supersede", tone: "neutral" },
];

export default function ContextBundlesPanel({ user }: { user: User }) {
  const [items, setItems] = useState<ContextBundle[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingAction, setSavingAction] = useState<ContextBundleAction | "">("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const selected = useMemo(
    () => items.find((item) => item.bundleId === selectedId) || items[0],
    [items, selectedId],
  );

  useEffect(() => {
    void loadItems();
  }, []);

  async function loadItems() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/context-bundles?limit=50", {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as ContextBundleListResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load context bundles");
      }
      const data = payload as ContextBundleListResponse;
      setItems(data.items);
      setSelectedId((current) =>
        data.items.some((item) => item.bundleId === current) ? current : data.items[0]?.bundleId || "",
      );
      setLastUpdated(data.generatedAt);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load context bundles");
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: ContextBundleAction) {
    if (!selected) {
      return;
    }
    setSavingAction(action);
    setError("");
    try {
      const response = await fetch(`/api/context-bundles/${selected.bundleId}/action`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          ...(await authHeader(user)),
        },
        body: JSON.stringify({ action, note }),
      });
      const payload = (await response.json()) as { error?: string };
      if (!response.ok) {
        throw new Error(payload.error || "Failed to update context bundle");
      }
      setNote("");
      await loadItems();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to update context bundle");
    } finally {
      setSavingAction("");
    }
  }

  return (
    <>
      <section className={styles.toolbar} aria-label="Context bundle actions">
        <div className={styles.headerStatsInline}>
          <span>{items.length} bundles</span>
          <span>{items.filter((item) => item.approvalStatus === "draft").length} drafts</span>
          <span>{items.filter((item) => item.approvalStatus === "approved").length} approved</span>
          <span>{lastUpdated ? formatDate(lastUpdated) : "Not loaded"}</span>
        </div>
        <button className={styles.refreshButton} onClick={loadItems} type="button">
          Refresh
        </button>
      </section>

      {error ? <div className={styles.error}>{error}</div> : null}

      <section className={styles.workspace}>
        <div className={styles.listPane}>
          <div className={styles.listHeader}>
            <span>Files</span>
            <span>Bundle</span>
            <span>Status</span>
          </div>
          {loading ? <div className={styles.empty}>Loading context bundles...</div> : null}
          {!loading && items.length === 0 ? (
            <div className={styles.empty}>No context bundles published yet.</div>
          ) : null}
          {items.map((item) => (
            <button
              key={item.bundleId}
              className={selected?.bundleId === item.bundleId ? styles.rowSelected : styles.rowButton}
              onClick={() => setSelectedId(item.bundleId)}
              type="button"
            >
              <span className={styles.priority}>{item.sourceFileCount}</span>
              <span>
                <strong>{item.bundleType || "context bundle"}</strong>
                <small>
                  {item.claimCount} claims / {item.relationshipCount} relationships
                </small>
              </span>
              <StatusPill status={item.approvalStatus} />
            </button>
          ))}
        </div>

        <aside className={styles.detailPane}>
          {selected ? (
            <>
              <div className={styles.detailTop}>
                <div>
                  <p className={styles.eyebrow}>Context bundle</p>
                  <h2>{selected.bundleType || selected.bundleId}</h2>
                </div>
                <StatusPill status={selected.approvalStatus} />
              </div>

              <dl className={styles.metaGrid}>
                <Field label="Bundle ID" value={selected.bundleId} />
                <Field label="Created" value={formatDate(selected.createdAt)} />
                <Field label="Created by" value={selected.createdBy || "-"} />
                <Field label="Requires approval" value={selected.requiresHumanApproval ? "true" : "false"} />
                <Field label="Source files" value={String(selected.sourceFileCount)} />
                <Field label="Claims" value={String(selected.claimCount)} />
                <Field label="Entities" value={String(selected.entityCount)} />
                <Field label="Relationships" value={String(selected.relationshipCount)} />
                <Field label="Evidence" value={String(selected.evidenceCount)} />
                <Field label="Omitted/blocked" value={String(selected.omittedCount)} />
                <Field label="Bytes" value={`${selected.actualBundleBytes} / ${selected.maxBundleBytes}`} />
                <Field label="Approved by" value={selected.approvedBy || "-"} />
              </dl>

              <label className={styles.noteLabel} htmlFor="context-bundle-note">
                Approval note
              </label>
              <textarea
                id="context-bundle-note"
                className={styles.note}
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Why this bundle should or should not become AI memory"
                rows={3}
              />

              <div className={styles.actions}>
                {ACTIONS.map((item) => (
                  <button
                    key={item.action}
                    className={styles[item.tone]}
                    disabled={Boolean(savingAction)}
                    onClick={() => runAction(item.action)}
                    type="button"
                  >
                    {savingAction === item.action ? "Saving..." : item.label}
                  </button>
                ))}
              </div>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>High confidence claims</p>
                {selected.recentClaims.length === 0 ? (
                  <div className={styles.emptyInline}>No claims in this bundle.</div>
                ) : null}
                {selected.recentClaims.slice(0, 20).map((claim) => (
                  <article className={styles.auditItem} key={claim.claimId}>
                    <div>
                      <strong>{claim.claimType || "claim"}</strong>
                      <span>{claim.text || "-"}</span>
                    </div>
                    <small>
                      confidence {formatConfidence(claim.confidence)} / evidence {claim.evidenceIds.length}
                    </small>
                  </article>
                ))}
              </section>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>Relationship graph</p>
                {selected.relationships.length === 0 ? (
                  <div className={styles.emptyInline}>No relationships in this bundle.</div>
                ) : null}
                {selected.relationships.slice(0, 20).map((relationship) => (
                  <article className={styles.auditItem} key={relationship.relationshipId}>
                    <div>
                      <strong>{relationship.relationshipType || "relationship"}</strong>
                      <span>
                        {relationship.fromId || "-"} to {relationship.toId || "-"}
                      </span>
                    </div>
                    <small>confidence {formatConfidence(relationship.confidence)}</small>
                  </article>
                ))}
              </section>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>Vault preview</p>
                <pre>{selected.vaultProjection?.content || "No vault projection for this bundle."}</pre>
              </section>
            </>
          ) : (
            <div className={styles.empty}>Select a context bundle.</div>
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

function formatConfidence(value: number) {
  return value ? value.toFixed(2) : "-";
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
