"use client";

import { useEffect, useMemo, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type { KnowledgeItem, KnowledgeListResponse } from "@/lib/knowledge/types";
import styles from "./review.module.css";

export default function KnowledgePanel({ user }: { user: User }) {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const selected = useMemo(
    () => items.find((item) => item.fileId === selectedId) || items[0],
    [items, selectedId],
  );

  useEffect(() => {
    void loadItems();
  }, []);

  async function loadItems() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/knowledge-items?limit=100", {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as KnowledgeListResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load knowledge");
      }
      const data = payload as KnowledgeListResponse;
      setItems(data.items);
      setSelectedId((current) =>
        data.items.some((item) => item.fileId === current) ? current : data.items[0]?.fileId || "",
      );
      setLastUpdated(data.generatedAt);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load knowledge");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className={styles.toolbar} aria-label="Knowledge actions">
        <div className={styles.headerStatsInline}>
          <span>{items.length} extracted files</span>
          <span>{totalEntities(items)} entities</span>
          <span>{totalRelationships(items)} relationships</span>
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
            <span>Chars</span>
            <span>Source</span>
            <span>Status</span>
          </div>
          {loading ? <div className={styles.empty}>Loading extracted knowledge...</div> : null}
          {!loading && items.length === 0 ? (
            <div className={styles.empty}>No extracted content yet.</div>
          ) : null}
          {items.map((item) => (
            <button
              key={item.fileId}
              className={selected?.fileId === item.fileId ? styles.rowSelected : styles.rowButton}
              onClick={() => setSelectedId(item.fileId)}
              type="button"
            >
              <span className={styles.priority}>{item.charCount}</span>
              <span>
                <strong>{item.title}</strong>
                <small>
                  {item.entityCount} entities / {item.relationshipCount} relationships
                </small>
              </span>
              <StatusPill status={item.extractionStatus} />
            </button>
          ))}
        </div>

        <aside className={styles.detailPane}>
          {selected ? (
            <>
              <div className={styles.detailTop}>
                <div>
                  <p className={styles.eyebrow}>Knowledge item</p>
                  <h2>{selected.title}</h2>
                </div>
                <StatusPill status={selected.extractionStatus} />
              </div>

              <dl className={styles.metaGrid}>
                <Field label="File ID" value={selected.fileId} />
                <Field label="Project" value={selected.projectId || "-"} />
                <Field label="Source status" value={selected.sourceStatus} />
                <Field label="Index eligible" value={selected.indexEligible ? "true" : "false"} />
                <Field label="Characters" value={String(selected.charCount)} />
                <Field label="Extracted" value={formatDate(selected.extractedAt)} />
              </dl>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>Content preview</p>
                <pre>{selected.preview || "No text preview."}</pre>
              </section>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>Entities</p>
                {selected.entities.length === 0 ? (
                  <div className={styles.emptyInline}>No entities extracted yet.</div>
                ) : null}
                {selected.entities.slice(0, 30).map((entity, index) => (
                  <article className={styles.auditItem} key={`${entity.name}-${index}`}>
                    <div>
                      <strong>{entity.name || "(unnamed)"}</strong>
                      <span>{entity.entityType || "entity"}</span>
                    </div>
                    <small>confidence {formatConfidence(entity.confidence)}</small>
                    {entity.evidence ? <p>{entity.evidence}</p> : null}
                  </article>
                ))}
              </section>

              <section className={styles.knowledgeBlock}>
                <p className={styles.eyebrow}>Relationships</p>
                {selected.relationships.length === 0 ? (
                  <div className={styles.emptyInline}>No relationships extracted yet.</div>
                ) : null}
                {selected.relationships.slice(0, 30).map((relationship, index) => (
                  <article className={styles.auditItem} key={`${relationship.from}-${relationship.to}-${index}`}>
                    <div>
                      <strong>{relationship.relationshipType || "relationship"}</strong>
                      <span>
                        {relationship.from || "-"} to {relationship.to || "-"}
                      </span>
                    </div>
                    <small>confidence {formatConfidence(relationship.confidence)}</small>
                    {relationship.reason ? <p>{relationship.reason}</p> : null}
                  </article>
                ))}
              </section>
            </>
          ) : (
            <div className={styles.empty}>Select a knowledge item.</div>
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

function totalEntities(items: KnowledgeItem[]) {
  return items.reduce((total, item) => total + item.entityCount, 0);
}

function totalRelationships(items: KnowledgeItem[]) {
  return items.reduce((total, item) => total + item.relationshipCount, 0);
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
