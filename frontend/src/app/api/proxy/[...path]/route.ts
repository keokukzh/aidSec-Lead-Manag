import { NextRequest, NextResponse } from "next/server";

function resolveBackendApiBase(): string {
  const raw =
    process.env.BACKEND_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000/api";

  const normalized = raw.trim().replace(/\/+$/, "");
  if (!normalized) return "";

  if (/\/api$/i.test(normalized)) return normalized;
  return `${normalized}/api`;
}

async function proxy(request: NextRequest, pathSegments: string[]) {
  const backendApiBase = resolveBackendApiBase();
  if (!backendApiBase) {
    return NextResponse.json(
      { detail: "Backend API URL is not configured" },
      { status: 500 }
    );
  }

  const path = pathSegments.join("/");
  const query = request.nextUrl.search || "";
  const targetUrl = `${backendApiBase}/${path}${query}`;

  const outgoingHeaders = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "host" || lower === "content-length") return;
    outgoingHeaders.set(key, value);
  });

  const method = request.method.toUpperCase();
  const hasBody = !["GET", "HEAD"].includes(method);

  const response = await fetch(targetUrl, {
    method,
    headers: outgoingHeaders,
    body: hasBody ? await request.arrayBuffer() : undefined,
    redirect: "manual",
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  response.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "content-length" || lower === "content-encoding" || lower === "transfer-encoding") {
      return;
    }
    responseHeaders.set(key, value);
  });

  const body = await response.arrayBuffer();

  return new NextResponse(body, {
    status: response.status,
    statusText: response.statusText,
    headers: responseHeaders,
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path || []);
}

export async function OPTIONS(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  return proxy(request, path || []);
}
