"use client";

import { useEffect, useState } from "react";
import type { User } from "firebase/auth";
import { authHeader } from "@/lib/auth/firebaseClient";
import type { ProgressSummaryResponse } from "@/lib/knowledge/types";
import styles from "./review.module.css";

export default function ProgressDashboard({ user }: { user: User }) {
  const [data, setData] = useState<ProgressSummaryResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setError("");
    try {
      const response = await fetch("/api/progress-summary", {
        headers: await authHeader(user),
        cache: "no-store",
      });
      const payload = (await response.json()) as ProgressSummaryResponse | { error?: string };
      if (!response.ok) {
        throw new Error("error" in payload ? payload.error : "Failed to load progress");
      }
      setData(payload as ProgressSummaryResponse);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load progress");
    }
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  const summary = data?.summary;
  return (
    <section className={styles.progressPanel} aria-label="System progress">
      <div className={styles.progressTop}>
        <div>
          <p className={styles.eyebrow}>System progress</p>
          <h2>Drive to Knowledge</h2>
        </div>
        <button className={styles.neutral} onClick={load} type="button">
          Refresh
        </button>
      </div>
      <div className={styles.progressGrid}>
        <Metric label="Scanned" value={summary?.filesTotal} />
        <Metric label="Active" value={summary?.active} tone="good" />
        <Metric label="Do not index" value={summary?.doNotIndex} />
        <Metric label="Needs review" value={summary?.needsHumanReview} tone="warn" />
        <Metric label="Extracted text" value={summary?.extractedText} tone="good" />
        <Metric label="Gemini records" value={summary?.entityExtractions} />
        <Metric label="Understood" value={summary?.understood} tone="good" />
        <Metric label="AI review" value={summary?.needsEntityReview} tone="warn" />
        <Metric label="Cleanup open" value={summary?.cleanupOpen} tone="warn" />
      </div>
      <div className={styles.progressBar} aria-hidden="true">
        <span style={{ width: `${percent(summary?.extractedText, summary?.active)}%` }} />
      </div>
      <p className={styles.progressNote}>
        Extracted {summary?.extractedText ?? "-"} of {summary?.active ?? "-"} active files.
      </p>
    </section>
  );
}

function Metric({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value?: number;
  tone?: "neutral" | "good" | "warn";
}) {
  return (
    <div className={`${styles.metric} ${styles[`metric_${tone}`] || ""}`}>
      <span>{label}</span>
      <strong>{value ?? "-"}</strong>
    </div>
  );
}

function percent(value?: number, total?: number) {
  if (!value || !total) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round((value / total) * 100)));
}
