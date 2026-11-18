import { describe, expect, it } from "vitest";
import { ApiError, errorMessage, fieldErrors, request, setCsrfToken } from "./client";
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

  it("TELA-02: envia FormData sem forçar Content-Type e com X-CSRF-Token", async () => {
    const { calls } = mockFetch({ "POST /api/processes/p1/documents": { status: 207, body: { results: [] } } });
    setCsrfToken("tok-2");
    const form = new FormData();
    form.append("file", new File(["%PDF-1.4"], "a.pdf", { type: "application/pdf" }));
    await request("POST", "/api/processes/p1/documents", form);
    const init = calls[0].init!;
    const headers = new Headers(init.headers);
    expect(init.body).toBe(form);
    expect(headers.has("Content-Type")).toBe(false);
    expect(headers.get("X-CSRF-Token")).toBe("tok-2");
    expect(init.credentials).toBe("include");
  });

  it("TELA-02: um corpo JSON continua com Content-Type application/json", async () => {
    const { calls } = mockFetch({ "PUT /api/x": { status: 200, body: {} } });
    setCsrfToken("tok-3");
    await request("PUT", "/api/x", { a: 1 });
    expect(new Headers(calls[0].init!.headers).get("Content-Type")).toBe("application/json");
  });

  it("TELA-02: o erro de um envio multipart vira ApiError com o status e o detalhe", async () => {
    mockFetch({ "POST /api/up": { status: 429, body: { detail: "Muitos envios" } } });
    const err = await request<never>("POST", "/api/up", new FormData()).catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
    expect(err.message).toBe("Muitos envios");
  });

  it("VER-11: 413 do nginx, com corpo HTML, vira ApiError 413 com a mensagem de limite de envio", async () => {
    mockFetch({ "POST /api/up": { status: 413, raw: "<html><h1>413 Request Entity Too Large</h1></html>" } });
    const err = await request<never>("POST", "/api/up", new FormData()).catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(413);
    expect(errorMessage(err)).toBe("O arquivo ou o conjunto excede o limite de envio.");
  });

  it("VER-11: um erro de rede segue com a mensagem de conexão", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toBe("Não foi possível contactar o servidor.");
  });

  it("VER-11: um 502 com corpo HTML vira ApiError 502, não um erro de leitura", async () => {
    mockFetch({ "GET /api/x": { status: 502, raw: "<html>Bad Gateway</html>" } });
    const err = await request<never>("GET", "/api/x").catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(errorMessage(err)).toBe("Erro 502");
  });

  it("UIG-05, TAB-07: um 422 com código mostra a mensagem em português do servidor", () => {
    const err = new ApiError(422, [
      {
        field: "geracao",
        code: "SEM_ATIVIDADES_VALIDADAS",
        message: "O processo não tem atividade validada.",
      },
    ]);
    expect(errorMessage(err)).toBe("O processo não tem atividade validada.");
  });

  it("UIG-05: um 422 de validação de campo, sem código, continua com o aviso dos campos destacados", () => {
    const err = new ApiError(422, [{ field: "siape", message: "SIAPE deve ter 7 dígitos" }]);
    expect(errorMessage(err)).toBe("Verifique os campos destacados.");
    expect(fieldErrors(err)).toEqual({ siape: "SIAPE deve ter 7 dígitos" });
  });

  it("UIG-05: com vários itens, vale a mensagem do primeiro que tem código", () => {
    const err = new ApiError(422, [
      { field: "siape", message: "SIAPE deve ter 7 dígitos" },
      { field: "geracao", code: "TABELA_NAO_ESCOLHIDA", message: "Escolha a tabela de pontuação." },
      { field: "geracao", code: "OUTRO", message: "Outra mensagem." },
    ]);
    expect(errorMessage(err)).toBe("Escolha a tabela de pontuação.");
  });

  it("UIG-05: um item com código mas sem mensagem cai no aviso dos campos destacados", () => {
    const err = new ApiError(422, [{ field: "geracao", code: "ERRO_INTERNO" }]);
    expect(errorMessage(err)).toBe("Verifique os campos destacados.");
  });

  it("UIG-05: um erro com detalhe em texto segue mostrando o texto", () => {
    expect(errorMessage(new ApiError(409, "Versão desatualizada"))).toBe("Versão desatualizada");
  });

  it("DEL-12: o 410 de um arquivo excluído mostra a mensagem em português do servidor", () => {
    const err = new ApiError(410, [
      { field: "arquivo", code: "ARQUIVO_EXCLUIDO", message: "O arquivo deste documento foi excluído na conclusão do processo" },
    ]);
    expect(errorMessage(err)).toBe("O arquivo deste documento foi excluído na conclusão do processo");
  });

  it("DEL-12: um 410 sem mensagem do servidor ainda diz que o arquivo foi excluído", () => {
    expect(errorMessage(new ApiError(410, undefined))).toBe("O arquivo deste documento foi excluído na conclusão do processo.");
  });
});
