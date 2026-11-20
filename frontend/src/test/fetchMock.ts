import { vi } from "vitest";

/** `body` is sent as JSON; `raw` is sent as is, as HTML (an nginx error page). */
export type MockResponse = { status: number; body?: unknown; raw?: string };
export type Route = (init: RequestInit | undefined) => MockResponse;

/** Stub global fetch with a "METHOD /path" -> response table; records every call. */
export function mockFetch(routes: Record<string, MockResponse | Route>) {
  const calls: { method: string; path: string; init: RequestInit | undefined }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const method = (init?.method ?? "GET").toUpperCase();
    const path = typeof input === "string" ? input : input.toString();
    calls.push({ method, path, init });
    const entry = routes[`${method} ${path}`];
    if (!entry) throw new Error(`Unexpected request: ${method} ${path}`);
    const { status, body, raw } = typeof entry === "function" ? entry(init) : entry;
    if (raw !== undefined) return new Response(raw, { status, headers: { "Content-Type": "text/html" } });
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return { fn, calls };
}

export const ME = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Admin",
  role: "ADMIN",
  csrf_token: "csrf-abc",
};

export const UNAUTHENTICATED: MockResponse = { status: 401, body: { detail: "Não autenticado" } };
