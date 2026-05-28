import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { updateSourceQuality } from "@/lib/sourceFiles/firestoreRest";
import type { SourceFileAction, SourceFileActionRequest } from "@/lib/sourceFiles/types";

export const dynamic = "force-dynamic";

const ALLOWED_ACTIONS = new Set<SourceFileAction>([
  "activate",
  "needs_review",
  "do_not_index",
]);

type RouteContext = {
  params: Promise<{
    fileId: string;
  }>;
};

export async function POST(request: Request, context: RouteContext) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const { fileId } = await context.params;

  try {
    const body = (await request.json()) as SourceFileActionRequest;
    if (!ALLOWED_ACTIONS.has(body.action)) {
      return NextResponse.json({ error: "Unsupported source file action" }, { status: 400 });
    }

    const result = await updateSourceQuality(fileId, body.action, body.note || "", auth.actor.email);
    return NextResponse.json({
      ok: true,
      fileId,
      ...result,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown source file action error" },
      { status: 500 },
    );
  }
}
