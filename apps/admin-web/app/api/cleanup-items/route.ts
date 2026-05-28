import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { listCleanupItems } from "@/lib/cleanupQueue/firestoreRest";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const url = new URL(request.url);
  const status = url.searchParams.get("status") || "open";
  const limit = Number.parseInt(url.searchParams.get("limit") || "100", 10);

  try {
    const items = await listCleanupItems(status, Number.isFinite(limit) ? limit : 100);
    return NextResponse.json({
      items,
      status,
      count: items.length,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown cleanup queue error" },
      { status: 500 },
    );
  }
}
