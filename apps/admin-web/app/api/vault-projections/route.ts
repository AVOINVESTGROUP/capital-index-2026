import { NextResponse } from "next/server";
import { requireAdmin } from "@/lib/auth/serverAuth";
import { getVaultProjectionState } from "@/lib/contextBundles/firestoreRest";

export async function GET(request: Request) {
  const auth = await requireAdmin(request);
  if (auth.response) {
    return auth.response;
  }

  try {
    return NextResponse.json(await getVaultProjectionState());
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown vault projection error" },
      { status: 500 },
    );
  }
}
