import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { updateCleanupItem } from "@/lib/cleanupQueue/firestoreRest";
import type { CleanupAction, CleanupActionRequest } from "@/lib/cleanupQueue/types";

export const dynamic = "force-dynamic";

const ALLOWED_ACTIONS = new Set<CleanupAction>([
  "keep_active",
  "mark_duplicate",
  "archive",
  "move_to_review",
  "do_not_index",
  "ignore",
]);

type RouteContext = {
  params: Promise<{
    cleanupId: string;
  }>;
};

export async function POST(request: Request, context: RouteContext) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const { cleanupId } = await context.params;

  try {
    const body = (await request.json()) as CleanupActionRequest;
    if (!ALLOWED_ACTIONS.has(body.action)) {
      return NextResponse.json({ error: "Unsupported cleanup action" }, { status: 400 });
    }

    const result = await updateCleanupItem(cleanupId, body.action, body.note || "", auth.actor.email);
    return NextResponse.json({
      ok: true,
      cleanupId,
      ...result,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown cleanup action error" },
      { status: 500 },
    );
  }
}
