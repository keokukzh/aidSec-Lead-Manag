import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");
  const errorDescription = searchParams.get("error_description");

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
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

  try {
    // Call backend to exchange code for token
    const response = await fetch(`${baseUrl}/emails/outlook/callback?code=${code}&state=${state || ""}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer backend-sync",
      },
    });

    if (response.ok) {
      redirectUrl.searchParams.set("outlook", "connected");
    } else {
      const errorData = await response.json().catch(() => ({ detail: "Token exchange failed" }));
      redirectUrl.searchParams.set("outlook", "error");
      redirectUrl.searchParams.set("message", errorData.detail || "Failed to connect Outlook");
    }
  } catch (err) {
    console.error("Callback processing error:", err);
    redirectUrl.searchParams.set("outlook", "error");
    redirectUrl.searchParams.set("message", "Internal server error during connection");
  }

  return NextResponse.redirect(redirectUrl);
}
