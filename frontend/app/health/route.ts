import { NextResponse } from "next/server";

/** App Runner / load balancer health (no auth). */
export function GET() {
  return NextResponse.json({ status: "ok" });
}
