import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { updateReviewItem } from "@/lib/reviewQueue/firestoreRest";
import type { ReviewAction, ReviewActionRequest } from "@/lib/reviewQueue/types";

export const dynamic = "force-dynamic";

const ALLOWED_ACTIONS = new Set<ReviewAction>([
  "approve",
  "reject",
  "needs_content",
  "close",
  "reopen",
]);

type RouteContext = {
  params: Promise<{
    reviewId: string;
  }>;
};

export async function POST(request: Request, context: RouteContext) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const { reviewId } = await context.params;

  try {
    const body = (await request.json()) as ReviewActionRequest;
    if (!ALLOWED_ACTIONS.has(body.action)) {
      return NextResponse.json({ error: "Unsupported review action" }, { status: 400 });
    }

    const result = await updateReviewItem(
      reviewId,
      body.action,
      body.note || "",
      auth.actor.email,
    );

    return NextResponse.json({
      ok: true,
      reviewId,
      ...result,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown review action error" },
      { status: 500 },
    );
  }
}
