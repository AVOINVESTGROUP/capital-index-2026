import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { listReviewActions } from "@/lib/reviewQueue/firestoreRest";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{
    reviewId: string;
  }>;
};

export async function GET(request: Request, context: RouteContext) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const { reviewId } = await context.params;

  try {
    const actions = await listReviewActions(reviewId);
    return NextResponse.json({
      actions,
      reviewId,
      count: actions.length,
      generatedAt: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown review actions error" },
      { status: 500 },
    );
  }
}
