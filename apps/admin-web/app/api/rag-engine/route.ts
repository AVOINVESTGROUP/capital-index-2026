import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { getRagEngineState } from "@/lib/ragEngine/rest";

export async function GET(request: Request) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  try {
    return NextResponse.json(await getRagEngineState());
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown RAG Engine error" },
      { status: 500 },
    );
  }
}
