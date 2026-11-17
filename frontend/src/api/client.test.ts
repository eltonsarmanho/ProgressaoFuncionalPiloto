import { describe, expect, it } from "vitest";
import { ApiError, fieldErrors, request, setCsrfToken } from "./client";
import { mockFetch } from "../test/fetchMock";

describe("api client", () => {
  it("envia cookie de sessão e o header X-CSRF-Token nas escritas", async () => {
    const { calls } = mockFetch({ "POST /api/professors": { status: 201, body: { id: "1" } } });
    setCsrfToken("tok-1");
    await request("POST", "/api/professors", { a: 1 });
    const init = calls[0].init!;
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("X-CSRF-Token")).toBe("tok-1");
    expect(init.body).toBe(JSON.stringify({ a: 1 }));
  });

  it("converte 422 em erros por campo", async () => {
    mockFetch({
      "POST /api/professors": {
        status: 422,
        body: { detail: [{ field: "siape", message: "SIAPE deve ter 7 dígitos" }] },
      },
    });
    const err = await request<never>("POST", "/api/professors", {}).catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(fieldErrors(err)).toEqual({ siape: "SIAPE deve ter 7 dígitos" });
  });
});
