import { cert, getApps, initializeApp } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { NextResponse } from "next/server";

export type AdminActor = {
  uid: string;
  email: string;
};

export type AdminAuthResult =
  | { actor: AdminActor; response?: never }
  | { actor?: never; response: NextResponse };

const PROJECT_ID = process.env.GCP_PROJECT_ID || "capital-index-2026";

export async function requireAdmin(request: Request): Promise<AdminAuthResult> {
  const token = bearerToken(request);
  if (!token) {
    return { response: NextResponse.json({ error: "Authentication required" }, { status: 401 }) };
  }

  try {
    const decoded = await getAuth(adminApp()).verifyIdToken(token);
    const email = decoded.email?.toLowerCase() || "";
    if (!email) {
      return { response: NextResponse.json({ error: "Email is required" }, { status: 403 }) };
    }
    if (!allowedEmails().has(email)) {
      return { response: NextResponse.json({ error: "Admin access denied" }, { status: 403 }) };
    }
    return { actor: { uid: decoded.uid, email } };
  } catch {
    return { response: NextResponse.json({ error: "Invalid authentication token" }, { status: 401 }) };
  }
}

function adminApp() {
  const existing = getApps()[0];
  if (existing) {
    return existing;
  }

  const credentialsJson = process.env.FIREBASE_ADMIN_CREDENTIALS_JSON;
  if (credentialsJson) {
    return initializeApp({
      credential: cert(JSON.parse(credentialsJson) as Parameters<typeof cert>[0]),
      projectId: PROJECT_ID,
    });
  }

  return initializeApp({ projectId: PROJECT_ID });
}

function bearerToken(request: Request): string {
  const header = request.headers.get("authorization") || "";
  const match = header.match(/^Bearer\s+(.+)$/i);
  return match?.[1]?.trim() || "";
}

function allowedEmails(): Set<string> {
  const raw = process.env.ADMIN_ALLOWED_EMAILS || "";
  return new Set(
    raw
      .split(",")
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean),
  );
}
