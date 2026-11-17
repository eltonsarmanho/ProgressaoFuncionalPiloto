/** Thin fetch wrapper: session cookie + CSRF header (AD-003), typed errors. */

export type FieldIssue = { field: string; message: string };

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  /** The whole response body, for the few errors that carry more than `detail` (409 duplicate). */
  readonly body: unknown;

  constructor(status: number, detail: unknown, body?: unknown) {
    super(typeof detail === "string" ? detail : `Erro ${status}`);
    this.status = status;
    this.detail = detail;
    this.body = body;
  }
}

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

/**
 * A `FormData` body is sent as is (multipart): the browser sets `Content-Type` with the boundary,
 * so it must never be forced here. Any other body is sent as JSON.
 */
export async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers = new Headers();
  const isForm = body instanceof FormData;
  if (body !== undefined && !isForm) headers.set("Content-Type", "application/json");
  if (method !== "GET" && csrfToken) headers.set("X-CSRF-Token", csrfToken);

  const response = await fetch(path, {
    method,
    headers,
    credentials: "include",
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!response.ok) throw new ApiError(response.status, data?.detail, data);
  return data as T;
}

/** Map a 422 `{detail:[{field,message}]}` to `{field: message}`; empty for other errors. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || error.status !== 422 || !Array.isArray(error.detail)) {
    return {};
  }
  return Object.fromEntries((error.detail as FieldIssue[]).map((i) => [i.field, i.message]));
}

/** Human message for any error (non-field). */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") return error.detail;
    if (error.status === 422) return "Verifique os campos destacados.";
    return `Erro ${error.status}`;
  }
  return "Não foi possível contactar o servidor.";
}
