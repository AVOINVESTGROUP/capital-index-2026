import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { listContextBundles } from "@/lib/contextBundles/firestoreRest";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const url = new URL(request.url);
  const limit = Number(url.searchParams.get("limit") || "50");

  try {
    const items = await listContextBundles(Math.max(1, Math.min(limit, 100)));
    return NextResponse.json({
      items,
      count: items.length,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown context bundle error" },
      { status: 500 },
    );
  }
}
