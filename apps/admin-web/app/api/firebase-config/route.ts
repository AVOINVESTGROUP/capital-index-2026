import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const config = firebaseWebConfig();
  if (!config) {
    return NextResponse.json({ error: "Firebase web config is not configured" }, { status: 500 });
  }
  return NextResponse.json(config);
}

function firebaseWebConfig(): Record<string, string> | null {
  if (process.env.FIREBASE_WEBAPP_CONFIG) {
    return JSON.parse(process.env.FIREBASE_WEBAPP_CONFIG) as Record<string, string>;
  }

  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
  const appId = process.env.NEXT_PUBLIC_FIREBASE_APP_ID;
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || process.env.GCP_PROJECT_ID;
  if (!apiKey || !appId || !projectId) {
    return null;
  }

  return {
    apiKey,
    appId,
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || `${projectId}.firebaseapp.com`,
    messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "",
    projectId,
    storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || `${projectId}.firebasestorage.app`,
  };
}
