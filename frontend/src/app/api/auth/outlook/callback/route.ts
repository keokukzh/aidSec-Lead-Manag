import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  const redirectUrl = new URL("/settings", request.url);

  if (error) {
    console.error("Outlook OAuth error:", error, errorDescription);
    redirectUrl.searchParams.set("outlook", "error");
    redirectUrl.searchParams.set("message", errorDescription || error);
    return NextResponse.redirect(redirectUrl);
  }

  if (!code) {
    redirectUrl.searchParams.set("outlook", "error");
    redirectUrl.searchParams.set("message", "No code received from Microsoft");
    return NextResponse.redirect(redirectUrl);
  }

  redirectUrl.searchParams.set("code", code);
  if (state) {
    redirectUrl.searchParams.set("state", state);
  }

  return NextResponse.redirect(redirectUrl);
}
