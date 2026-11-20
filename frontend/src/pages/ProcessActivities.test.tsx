import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, Validity } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ProcessActivities } from "./ProcessActivities";

const VALID: Validity = { state: "VALIDA", reason: null, needs_category: false, params: {} };
const NEEDS: Validity = { ...VALID, needs_category: true };

function activity(over: Partial<Activity> = {}): Activity {
  return {
    id: "a1", process_id: "p1", title: "Banca de mestrado", group_number: 3, item_number: 2, description: "", event_date: "2025-05-10",
    period_start: null, period_end: null, period_precision: "DAY", academic_period: null, level: null, quantidade: "1.00", horas: null,
    course_hours: null, informed_points: null, points_override: null, evidence_note: null, source: "SUGERIDA_IA",
    status: "AGUARDANDO_REVISAO", distinct_justification: null, candidates: [],
    evidences: [{ id: "e1", document_id: "d1", document_name: "ata.pdf", page: 2, excerpt: "" }], version: 2,
    validity: VALID, merged: [], predicted_points: "4.00", ...over,
  };
}

const noCategory = (id: string, title: string) =>
  activity({ id, title, group_number: null, item_number: null, validity: NEEDS, predicted_points: null });

const VERSION = {
  id: "v1", table_id: "t1", name: "FASI 2022", valid_from: "2022-01-01", valid_to: null, norm_reference: "Res.", status: "VALIDADA",
  minimums: null, notes: null,
  groups: [
    {
      number: 3, name: "Bancas", counts_in_total: true, max_points: null,
      criteria: [
        { group_number: 3, item_number: 2, description: "Banca de mestrado", unit_label: "banca", mode: "POR_UNIDADE", unit_points: "4.00", hours_per_block: null, weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null, accepted_evidence: null, rules: null, review_note: null },
      ],
    },
  ],
};
const TABLE = { chosen: { table_name: "FASI", version: { id: "v1" } }, suggested: null, alerts: [] };
const RESULT = {
  rows: [{ activity_id: "a1", title: "Banca de mestrado", activity_status: "AGUARDANDO_REVISAO", evidence_note: null, group_number: 3, item_number: 2, unit_points: "4.00", effective_quantity: "1.00", formula_text: null, points: "4.00", pit_hours: null, status: "POTENCIAL", reasons: [], alerts: [] }],
};

const process = (status: string) => ({ id: "p1", status });
const LIST = "GET /api/processes/p1/activities";
const MERGE = "POST /api/processes/p1/activities/merge-duplicates";
const ROUTES = {
  "GET /api/processes/p1": { status: 200, body: process("EM_ANDAMENTO") },
  [MERGE]: { status: 200, body: { merged: 0 } },
  "GET /api/processes/p1/documents": { status: 200, body: [{ id: "d1", original_name: "ata.pdf" }] },
  "GET /api/processes/p1/scoring/table": { status: 200, body: TABLE },
  "GET /api/scoring-versions/v1": { status: 200, body: VERSION },
  "GET /api/processes/p1/scoring": { status: 200, body: RESULT },
};
const keyOf = (c: { method: string; path: string }) => `${c.method} ${c.path}`;
const count = (calls: { method: string; path: string }[], key: string) => calls.filter((c) => keyOf(c) === key).length;

function renderPage(routes: Parameters<typeof mockFetch>[0]) {
  setCsrfToken("tok");
  const mock = mockFetch({ ...ROUTES, ...routes });
  render(
    <MemoryRouter initialEntries={["/processos/p1/atividades"]}>
      <Routes>
        <Route path="processos/:id/atividades" element={<ProcessActivities />} />
      </Routes>
    </MemoryRouter>,
  );
  return { ...mock, user: userEvent.setup() };
}

const nav = () => screen.getByRole("navigation", { name: "Etapas do processo" });

describe("TELA-06: página da Etapa 3", () => {
  it("mostra as atividades nas duas seções, a navegação na Etapa 3 e o link para a Etapa 4", async () => {
    renderPage({ [LIST]: { status: 200, body: [activity()] } });
    expect(await screen.findByText("Banca de mestrado")).toBeInTheDocument();
    expect(screen.getByText("ata.pdf, página 2")).toBeInTheDocument();
    expect(screen.getByText("Pontos previstos: 4,00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Etapa 3 · Atividades" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (1)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Atividades não válidas (0)" })).toBeInTheDocument();
    expect(within(nav()).getAllByRole("listitem")[2]).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).toHaveAttribute("href", "/processos/p1/pontuacao");
  });

  it("sem o resultado da pontuação a lista continua funcionando, e sem a tabela não há seletor de categoria", async () => {
    renderPage({ [LIST]: { status: 200, body: [noCategory("c1", "Sem enquadramento")] }, "GET /api/processes/p1/scoring": { status: 500, body: { detail: "falha" } }, "GET /api/processes/p1/scoring/table": { status: 200, body: { chosen: null, suggested: null, alerts: [] } } });
    expect(await screen.findByText("Sem enquadramento")).toBeInTheDocument();
    expect(screen.getByText("Escolha a tabela de pontuação na Etapa 4 para poder escolher a categoria.")).toBeInTheDocument();
  });

  it("erro ao carregar as atividades aparece como alerta", async () => {
    renderPage({ [LIST]: { status: 404, body: { detail: "Processo não encontrado" } } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Processo não encontrado");
  });
});

describe("DUP-04: a mesclagem na abertura", () => {
  it("abre a página chamando a mesclagem uma vez e só depois a lista", async () => {
    const { calls } = renderPage({ [LIST]: { status: 200, body: [activity()] } });
    await screen.findByText("Banca de mestrado");
    expect(count(calls, MERGE)).toBe(1);
    const order = calls.map(keyOf);
    expect(order.indexOf(MERGE)).toBeLessThan(order.indexOf(LIST));
  });

  it("validar recarrega a lista e mostra o novo status, sem chamar a mesclagem de novo", async () => {
    let validated = false;
    const { calls, user } = renderPage({
      [LIST]: () => ({ status: 200, body: [activity({ status: validated ? "VALIDADA" : "AGUARDANDO_REVISAO" })] }),
      "POST /api/activities/a1/status": () => {
        validated = true;
        return { status: 200, body: activity({ status: "VALIDADA" }) };
      },
    });
    await user.click(await screen.findByRole("button", { name: "Validar Banca de mestrado" }));
    await waitFor(() => expect(screen.getByText("Validada")).toBeInTheDocument());
    expect(count(calls, LIST)).toBe(2);
    expect(count(calls, MERGE)).toBe(1);
  });

  it("processo somente leitura não chama a mesclagem e ainda mostra a lista", async () => {
    for (const status of ["CONCLUIDO", "ARQUIVADO"]) {
      const { calls } = renderPage({
        "GET /api/processes/p1": { status: 200, body: process(status) },
        [LIST]: { status: 200, body: [activity()] },
      });
      expect(await screen.findByText("Banca de mestrado")).toBeInTheDocument();
      expect(count(calls, MERGE)).toBe(0);
      cleanup();
    }
  });

  it("a falha da mesclagem não impede carregar a lista", async () => {
    renderPage({ [MERGE]: { status: 500, body: { detail: "falha ao mesclar" } }, [LIST]: { status: 200, body: [activity()] } });
    expect(await screen.findByText("Banca de mestrado")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("a falha de ler o processo também deixa a lista aparecer", async () => {
    renderPage({ "GET /api/processes/p1": { status: 500, body: { detail: "falha" } }, [LIST]: { status: 200, body: [activity()] } });
    expect(await screen.findByText("Banca de mestrado")).toBeInTheDocument();
  });
});

describe("SEC-05: o avanço bloqueado sem categoria", () => {
  const THREE = () => [noCategory("c1", "Uma"), noCategory("c2", "Duas"), noCategory("c3", "Três"), activity()];

  it("com 3 atividades sem categoria bloqueia as etapas 4 e 5 com a mensagem e tira o link da Etapa 4", async () => {
    renderPage({ [LIST]: { status: 200, body: THREE() } });
    await screen.findByText("Uma");
    expect(within(nav()).getByText("3 atividades precisam de categoria")).toBeInTheDocument();
    const items = within(nav()).getAllByRole("listitem");
    expect(items[3]).toHaveAttribute("aria-disabled", "true");
    expect(items[4]).toHaveAttribute("aria-disabled", "true");
    expect(screen.queryByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).not.toBeInTheDocument();
    expect(screen.getByText("Ir para a Etapa 4 · Pontuação")).toHaveAttribute("aria-disabled", "true");
  });

  it("escolher a categoria na linha grava, recarrega e libera o avanço sem recarregar a página", async () => {
    let chosen = false;
    const { calls, user } = renderPage({
      [LIST]: () => ({ status: 200, body: chosen ? [activity({ id: "c1", title: "Uma" })] : [noCategory("c1", "Uma")] }),
      "PUT /api/activities/c1": () => {
        chosen = true;
        return { status: 200, body: activity({ id: "c1", title: "Uma" }) };
      },
    });
    await screen.findByText("Uma");
    expect(within(nav()).getByText("1 atividade precisa de categoria")).toBeInTheDocument();
    await user.selectOptions(screen.getByRole("combobox", { name: "Categoria de Uma" }), "3.2");
    await waitFor(() => expect(within(nav()).queryByText(/precisa de categoria/)).not.toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).toBeInTheDocument();
    expect(within(nav()).getAllByRole("listitem")[3]).not.toHaveAttribute("aria-disabled");
    expect(count(calls, MERGE)).toBe(1);
  });

  it("o item 'Ir para a Etapa 4' fechado e as etapas fechadas apontam a mensagem do bloqueio", async () => {
    renderPage({ [LIST]: { status: 200, body: [noCategory("c1", "Uma")] } });
    await screen.findByText("Uma");
    const message = nav().querySelector<HTMLElement>("[aria-live=polite]")!;
    expect(message).toHaveTextContent("1 atividade precisa de categoria");
    expect(screen.getByText("Ir para a Etapa 4 · Pontuação")).toHaveAttribute("aria-describedby", message.id);
    expect(within(nav()).getAllByRole("listitem")[3]).toHaveAttribute("aria-describedby", message.id);
  });

  it("uma atividade sem categoria que não é válida não bloqueia o avanço", async () => {
    const out = activity({
      id: "o1", title: "Fora", group_number: null, item_number: null, predicted_points: null,
      validity: { state: "NAO_VALIDA", reason: "FORA_DO_INTERSTICIO", needs_category: true, params: { event_date: "2023-01-01", interstice_start: "2024-01-01", interstice_end: "2025-12-31" } },
    });
    renderPage({ [LIST]: { status: 200, body: [out] } });
    await screen.findByRole("heading", { level: 2, name: /^Atividades não válidas \(1\)/ });
    expect(within(nav()).queryByText(/precisa de categoria/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).toBeInTheDocument();
  });
});

describe("SEC-05: sem tabela escolhida o avanço não fica sem saída", () => {
  const NO_TABLE = { "GET /api/processes/p1/scoring/table": { status: 200, body: { chosen: null, suggested: null, alerts: [] } } };

  it("sem tabela, com atividade sem categoria, o avanço à Etapa 4 segue livre e a página explica e leva à Etapa 4", async () => {
    renderPage({ ...NO_TABLE, [LIST]: { status: 200, body: [noCategory("c1", "Uma"), noCategory("c2", "Duas")] } });
    await screen.findByText("Uma");
    expect(within(nav()).queryByText(/precisam? de categoria/)).not.toBeInTheDocument();
    expect(within(nav()).getAllByRole("listitem")[3]).not.toHaveAttribute("aria-disabled");
    expect(screen.getByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).toHaveAttribute("href", "/processos/p1/pontuacao");
    expect(screen.getByText("Nenhuma tabela de pontuação foi escolhida, por isso as categorias ainda não podem ser definidas.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher a tabela na Etapa 4" })).toHaveAttribute("href", "/processos/p1/pontuacao");
  });

  it("com tabela, o aviso de tabela não aparece e a atividade sem categoria bloqueia com 'N atividades precisam de categoria'", async () => {
    renderPage({ [LIST]: { status: 200, body: [noCategory("c1", "Uma"), noCategory("c2", "Duas")] } });
    await screen.findByText("Uma");
    expect(screen.queryByText(/Nenhuma tabela de pontuação foi escolhida/)).not.toBeInTheDocument();
    expect(within(nav()).getByText("2 atividades precisam de categoria")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).not.toBeInTheDocument();
  });
});

describe("SEC-05: a falha de ler as categorias de uma tabela escolhida", () => {
  it("com tabela escolhida e as versões falhando, não diz que falta a tabela, mostra o erro e mantém o bloqueio", async () => {
    renderPage({
      "GET /api/scoring-versions/v1": { status: 500, body: { detail: "falha" } },
      [LIST]: { status: 200, body: [noCategory("c1", "Uma")] },
    });
    await screen.findByText("Uma");
    expect(screen.queryByText(/Nenhuma tabela de pontuação foi escolhida/)).not.toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar as categorias da tabela de pontuação.");
    expect(within(nav()).getByText("1 atividade precisa de categoria")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).not.toBeInTheDocument();
  });
});

describe("REV: rejeitar, editar e validar em lote recarregam a lista", () => {
  it("rejeitar recarrega a lista", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [activity()] },
      "POST /api/activities/a1/status": { status: 200, body: activity({ status: "REJEITADA" }) },
    });
    await user.click(await screen.findByRole("button", { name: "Rejeitar Banca de mestrado" }));
    await waitFor(() => expect(count(calls, LIST)).toBe(2));
  });

  it("editar recarrega a lista depois de salvar, sem justificativa", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [activity()] },
      "PUT /api/activities/a1": { status: 200, body: activity({ title: "Banca corrigida" }) },
    });
    await user.click(await screen.findByRole("button", { name: "Editar Banca de mestrado" }));
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() => expect(count(calls, LIST)).toBe(2));
  });

  it("validar as selecionadas chama a rota em lote só com os ids, sem justificativa, e recarrega", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [activity(), activity({ id: "a2", title: "Segunda banca" })] },
      "POST /api/processes/p1/activities/validate-batch": { status: 200, body: { activities: [{ id: "a1" }, { id: "a2" }], skipped: [] } },
    });
    await user.click(await screen.findByLabelText("Selecionar Banca de mestrado"));
    await user.click(screen.getByLabelText("Selecionar Segunda banca"));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));

    await waitFor(() => expect(count(calls, LIST)).toBe(2));
    const batch = calls.find((c) => c.path === "/api/processes/p1/activities/validate-batch")!;
    expect(JSON.parse(batch.init?.body as string)).toEqual({ activity_ids: ["a1", "a2"] });
    expect(await screen.findByText(/2 validadas/)).toBeInTheDocument();
  });
});
