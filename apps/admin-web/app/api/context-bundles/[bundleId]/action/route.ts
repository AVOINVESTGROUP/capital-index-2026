import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { updateContextBundle } from "@/lib/contextBundles/firestoreRest";
import type { ContextBundleAction, ContextBundleActionRequest } from "@/lib/contextBundles/types";

export const dynamic = "force-dynamic";

const ALLOWED_ACTIONS = new Set<ContextBundleAction>(["approve", "reject", "supersede"]);

type RouteContext = {
  params: Promise<{
    bundleId: string;
  }>;
};

export async function POST(request: Request, context: RouteContext) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  const { bundleId } = await context.params;

  try {
    const body = (await request.json()) as ContextBundleActionRequest;
    if (!ALLOWED_ACTIONS.has(body.action)) {
      return NextResponse.json({ error: "Unsupported context bundle action" }, { status: 400 });
    }
    const result = await updateContextBundle(bundleId, body.action, body.note || "", auth.actor.email);
    return NextResponse.json({
      ok: true,
      bundleId,
      ...result,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown context bundle action error" },
      { status: 500 },
    );
  }
}
