import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { listSourceFiles } from "@/lib/sourceFiles/firestoreRest";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const url = new URL(request.url);
  const status = url.searchParams.get("status") || "needs_human_review";
  const limit = Number.parseInt(url.searchParams.get("limit") || "100", 10);

  try {
    const items = await listSourceFiles(status, Number.isFinite(limit) ? limit : 100);
    return NextResponse.json({
      items,
      status,
      count: items.length,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown source files error" },
      { status: 500 },
    );
  }
}
