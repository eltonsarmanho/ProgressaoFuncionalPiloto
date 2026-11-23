import { describe, expect, it } from "vitest";
import {
  getBoard,
  getDossier,
  rereadOrdinance,
  saveCity,
  saveOpinion,
  saveOrdinance,
  setDelivered,
  uploadOrdinance,
  type BoardView,
  type ChecklistItem,
} from "./board";
import { ApiError, fieldErrors } from "./client";
import { mockFetch } from "../test/fetchMock";

const BOARD: BoardView = {
  ordinance: {
    number: "12/2026",
    number_page: 1,
    number_source: "EXTRAIDO",
    ordinance_date: "2026-10-05",
    date_page: 1,
    date_source: "EXTRAIDO",
    members: [{ name: "Ana Souza", role: "PRESIDENTE", page: 2, source: "EXTRAIDO" }],
    file: { original_name: "portaria.pdf", mime: "application/pdf", size_bytes: 2048, page_count: 2, deleted: false },
    reading_state: "LIDA",
    reading_code: null,
    warnings: [],
    version: 3,
  },
  opinion: { conclusion: null, opinion_date: null, place: null, version: 1 },
  request_settings: { city: null, version: 1 },
};

const ITEM: ChecklistItem = {
  key: "CURRICULO_LATTES",
  order: 7,
  title: "Currículo Lattes atualizado",
  source: "MANUAL",
  state: "ENTREGUE",
  version_number: null,
  generation_id: null,
  outdated_table: false,
};

describe("PORT-02, PAR-01, DOS-02: cliente da API da banca e do dossiê", () => {
  it("getBoard lê a portaria, a minuta e a cidade do processo", async () => {
    const { calls } = mockFetch({ "GET /api/processes/p1/board": { status: 200, body: BOARD } });
    expect(await getBoard("p1")).toEqual(BOARD);
    expect(calls).toHaveLength(1);
  });

  it("saveOrdinance faz PUT dos dados com a versão e sem justificativa", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/board/ordinance": { status: 200, body: BOARD.ordinance } });
    const body = {
      number: "12/2026",
      ordinance_date: "2026-10-05",
      members: [{ name: "Ana Souza", role: "PRESIDENTE" as const }],
      expected_version: 3,
    };
    await saveOrdinance("p1", body);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual(body);
  });

  it("PORT-01: uploadOrdinance envia FormData com o arquivo, expected_version e replace, sem forçar Content-Type", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/board/ordinance/file": { status: 200, body: BOARD.ordinance } });
    const file = new File(["%PDF-1.4"], "portaria.pdf", { type: "application/pdf" });
    await uploadOrdinance("p1", file, 0, true);
    const init = calls[0].init!;
    expect(init.body).toBeInstanceOf(FormData);
    const form = init.body as FormData;
    expect(form.get("file")).toBe(file);
    expect(form.get("expected_version")).toBe("0");
    expect(form.get("replace")).toBe("true");
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
  });

  it("uploadOrdinance sem substituição envia replace falso", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/board/ordinance/file": { status: 200, body: BOARD.ordinance } });
    await uploadOrdinance("p1", new File(["x"], "p.png", { type: "image/png" }), 2, false);
    expect((calls[0].init!.body as FormData).get("replace")).toBe("false");
    expect((calls[0].init!.body as FormData).get("expected_version")).toBe("2");
  });

  it("PORT-07: rereadOrdinance faz POST da nova leitura com a versão", async () => {
    const { calls } = mockFetch({ "POST /api/processes/p1/board/ordinance/reread": { status: 200, body: BOARD.ordinance } });
    await rereadOrdinance("p1", 3);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ expected_version: 3 });
  });

  it("PAR-01: saveOpinion faz PUT da conclusão, da data e do local com a versão, sem observações", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/board/opinion": { status: 200, body: BOARD.opinion } });
    const body = { conclusion: "FAVORAVEL" as const, opinion_date: "2026-11-20", place: "Belém", expected_version: 1 };
    await saveOpinion("p1", body);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual(body);
  });

  it("saveCity faz PUT da cidade em request-settings com a versão", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/request-settings": { status: 200, body: { city: "Belém", version: 2 } } });
    await saveCity("p1", "Belém", 1);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ city: "Belém", expected_version: 1 });
  });

  it("DOS-02: getDossier lê o checklist do processo", async () => {
    mockFetch({ "GET /api/processes/p1/dossier": { status: 200, body: [ITEM] } });
    expect(await getDossier("p1")).toEqual([ITEM]);
  });

  it("DOS-04: setDelivered faz PUT de {entregue: true} no item e devolve a lista nova", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/dossier/items/CURRICULO_LATTES": { status: 200, body: [ITEM] } });
    expect(await setDelivered("p1", "CURRICULO_LATTES", true)).toEqual([ITEM]);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ entregue: true });
  });

  it("DOS-04: setDelivered desmarca com {entregue: false}", async () => {
    const { calls } = mockFetch({ "PUT /api/processes/p1/dossier/items/CURRICULO_LATTES": { status: 200, body: [] } });
    await setDelivered("p1", "CURRICULO_LATTES", false);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ entregue: false });
  });

  it("PORT-12: o 409 VERSAO_DESATUALIZADA chega como ApiError com o código", async () => {
    mockFetch({
      "PUT /api/processes/p1/board/ordinance": {
        status: 409,
        body: { detail: "Versão desatualizada", code: "VERSAO_DESATUALIZADA" },
      },
    });
    const err = await saveOrdinance("p1", { number: null, ordinance_date: null, members: [], expected_version: 1 }).catch(
      (e: unknown) => e,
    );
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(409);
    expect(((err as ApiError).body as { code: string }).code).toBe("VERSAO_DESATUALIZADA");
  });

  it("PORT-11: o 422 por campo chega como ApiError com o campo do membro", async () => {
    mockFetch({
      "PUT /api/processes/p1/board/ordinance": {
        status: 422,
        body: { detail: [{ field: "members[1].name", message: "Nome do membro é obrigatório" }] },
      },
    });
    const err = await saveOrdinance("p1", { number: null, ordinance_date: null, members: [], expected_version: 1 }).catch(
      (e: unknown) => e,
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(fieldErrors(err)).toEqual({ "members[1].name": "Nome do membro é obrigatório" });
  });
});
