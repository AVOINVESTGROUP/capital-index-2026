import { NextRequest, NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { listKnowledgeItems } from "@/lib/knowledge/firestoreRest";

export async function GET(request: NextRequest) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const limit = Number(request.nextUrl.searchParams.get("limit") || "50");
  try {
    const items = await listKnowledgeItems(Math.max(1, Math.min(limit, 100)));
    return NextResponse.json({
      items,
      count: items.length,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown knowledge error" },
      { status: 500 },
    );
  }
}
