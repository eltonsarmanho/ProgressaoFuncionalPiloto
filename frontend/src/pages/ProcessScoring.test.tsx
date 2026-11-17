import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import type { Activity, ScoringResult } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ProcessScoring } from "./ProcessScoring";

const VERSION_INFO = {
  id: "v-fasi",
  table_id: "t-fasi",
  name: "FASI 2022",
  valid_from: "2022-01-01",
  valid_to: null,
  norm_reference: "Res. FASI 2022, Anexo I",
  status: "PENDENTE_VALIDACAO" as const,
};
const CHOSEN = { table_name: "Tabela FASI", version: VERSION_INFO };

const CHOICE = {
  chosen: CHOSEN,
  suggested: CHOSEN,
  alerts: [
    { code: "TABELA_PENDENTE_VALIDACAO", severity: "REQUER_ANALISE_NORMATIVA", message: "A tabela aguarda validação", norm_reference: "Res. FASI 2022" },
  ],
};

const VERSION = {
  ...VERSION_INFO,
  minimums: null,
  notes: null,
  groups: [
    { number: 1, name: "Docência", counts_in_total: true, max_points: null, criteria: [] },
    {
      number: 2,
      name: "Orientação",
      counts_in_total: true,
      max_points: null,
      criteria: [
        { group_number: 2, item_number: 7, description: "Orientação de TCC", unit_label: "orientação", mode: "POR_UNIDADE", unit_points: "10.00", hours_per_block: null, weeks_per_semester: null, prep_ratio: null, max_points: null, accepted_evidence: null, rules: null, review_note: null },
      ],
    },
  ],
};

function result(total: string, rows: ScoringResult["rows"]): ScoringResult {
  return {
    process_id: "proc-1",
    chosen: CHOSEN,
    suggested: CHOSEN,
    subtotals: [
      { group_number: 1, subtotal: "0.00" },
      { group_number: 2, subtotal: total },
    ],
    total,
    potential_total: total,
    potential_dated: total,
    potential_undated: "0.00",
    group1_percent: null,
    group1_hours_by_period: {},
    group1_total_hours: "0.00",
    counters: { activities: rows.length, with_evidence: 0, pending: 0, not_scored: 0, with_alerts: 1 },
    rows,
    limit_adjustments: [],
    alerts: [
      { code: "SEM_EXTENSAO_OU_PESQUISA", severity: "ALERTA", message: "Sem extensão ou pesquisa", norm_reference: "Res. 4.644/2015, art. 13, II" },
    ],
    minimum: { status: "NAO_DEFINIDO", minimum: null, total },
  };
}

const ROW: ScoringResult["rows"][number] = {
  activity_id: "a1",
  title: "Orientação de TCC",
  activity_status: "VALIDADA",
  evidence_note: null,
  group_number: 2,
  item_number: 7,
  unit_points: "10.00",
  effective_quantity: "4.00",
  formula_text: "4 x 10",
  points: "40.00",
  pit_hours: null,
  status: "PONTUADA",
  reasons: [],
  alerts: [
    { code: "SEM_COMPROVANTE", severity: "ALERTA", message: "Atividade sem comprovante", norm_reference: "Res. 4.644/2015, art. 5º" },
  ],
};

const ACTIVITY: Activity = {
  id: "a1",
  process_id: "proc-1",
  title: "Orientação de TCC",
  group_number: 2,
  item_number: 7,
  description: null,
  event_date: "2023-05-10",
  period_start: null,
  period_end: null,
  period_precision: "DAY",
  academic_period: null,
  level: null,
  quantidade: "4.00",
  horas: null,
  course_hours: null,
  informed_points: null,
  points_override: null,
  evidence_note: null,
  source: "MANUAL",
  status: "VALIDADA",
  distinct_justification: null,
  candidates: [],
  version: 3,
};

function baseRoutes(scoring: () => ScoringResult) {
  return {
    "GET /api/processes/proc-1/scoring/table": { status: 200, body: CHOICE },
    "GET /api/processes/proc-1/scoring": () => ({ status: 200, body: scoring() }),
    "GET /api/scoring-versions/v-fasi": { status: 200, body: VERSION },
    "GET /api/scoring-tables": { status: 200, body: [] },
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/processos/proc-1/pontuacao"]}>
      <Routes>
        <Route path="processos/:id/pontuacao" element={<ProcessScoring />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProcessScoring", () => {
  it("TELA-02/03: carrega e exibe a tabela, os subtotais e o total em pt-BR com os nomes dos grupos da versão", async () => {
    mockFetch(baseRoutes(() => result("40.00", [ROW])));
    renderPage();
    const row = (await screen.findByText("Orientação de TCC", { selector: "td" })).closest("tr")!;
    expect(row).toHaveTextContent("40,00");
    expect(screen.getByRole("columnheader", { name: "Pontuação unitária" })).toBeInTheDocument();
    expect(screen.getByText("Grupo II · Orientação", { selector: "dt" }).nextElementSibling).toHaveTextContent("40,00");
    expect(screen.getByText("Total geral", { selector: "dt" }).nextElementSibling).toHaveTextContent("40,00");
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getAllByRole("listitem")[3]).toHaveAttribute("aria-current", "step");
  });

  it("TELA-07: exibe os alertas da tabela, do processo e das atividades agrupados por severidade com a referência", async () => {
    mockFetch(baseRoutes(() => result("40.00", [ROW])));
    renderPage();
    const analise = await screen.findByRole("region", { name: "Requer análise normativa (1)" });
    expect(analise).toHaveTextContent("TABELA_PENDENTE_VALIDACAO");
    expect(analise).toHaveTextContent("Referência normativa: Res. FASI 2022");
    const alerta = screen.getByRole("region", { name: "Alerta (2)" });
    expect(alerta).toHaveTextContent("SEM_EXTENSAO_OU_PESQUISA");
    expect(alerta).toHaveTextContent("Referência normativa: Res. 4.644/2015, art. 13, II");
    expect(alerta).toHaveTextContent("Orientação de TCC: Atividade sem comprovante");
    expect(alerta).toHaveTextContent("Referência normativa: Res. 4.644/2015, art. 5º");
  });

  it("TELA-04: cria uma atividade e recarrega o resultado com o novo total", async () => {
    let total = "40.00";
    const { calls } = mockFetch({
      ...baseRoutes(() => result(total, [ROW])),
      "POST /api/processes/proc-1/activities": () => {
        total = "80.00";
        return { status: 201, body: ACTIVITY };
      },
    });
    renderPage();
    const user = userEvent.setup();
    await screen.findByText("Orientação de TCC", { selector: "td" });
    await user.click(screen.getByRole("button", { name: "Nova atividade" }));
    await user.type(screen.getByLabelText("Título"), "Outra orientação");
    await user.selectOptions(screen.getByLabelText("Grupo"), "2");
    await user.selectOptions(screen.getByLabelText("Item"), "7");
    await user.type(screen.getByLabelText("Quantidade"), "8");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() =>
      expect(screen.getByText("Total geral", { selector: "dt" }).nextElementSibling).toHaveTextContent("80,00"),
    );
    const post = calls.find((c) => c.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toEqual({
      title: "Outra orientação",
      group_number: 2,
      item_number: 7,
      quantidade: 8,
    });
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/processes/proc-1/scoring")).toHaveLength(2);
  });

  it("TELA-04: edita uma atividade com justificativa e recarrega o resultado", async () => {
    let total = "40.00";
    const { calls } = mockFetch({
      ...baseRoutes(() => result(total, [ROW])),
      "GET /api/activities/a1": { status: 200, body: ACTIVITY },
      "PUT /api/activities/a1": () => {
        total = "50.00";
        return { status: 200, body: { ...ACTIVITY, quantidade: "5.00", version: 4 } };
      },
    });
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Editar Orientação de TCC" }));
    const quantidade = await screen.findByLabelText("Quantidade");
    await user.clear(quantidade);
    await user.type(quantidade, "5");
    await user.type(screen.getByLabelText("Justificativa da alteração"), "Ata corrigida");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() =>
      expect(screen.getByText("Total geral", { selector: "dt" }).nextElementSibling).toHaveTextContent("50,00"),
    );
    const put = calls.find((c) => c.method === "PUT")!;
    expect(JSON.parse(put.init!.body as string)).toMatchObject({
      quantidade: 5,
      justificativa: "Ata corrigida",
      expected_version: 3,
    });
    expect(screen.queryByLabelText("Justificativa da alteração")).not.toBeInTheDocument();
  });

  it("validar e rejeitar chamam o endpoint de status com justificativa e expected_version", async () => {
    const { calls } = mockFetch({
      ...baseRoutes(() => result("40.00", [ROW])),
      "GET /api/activities/a1": { status: 200, body: ACTIVITY },
      "POST /api/activities/a1/status": { status: 200, body: ACTIVITY },
    });
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Rejeitar Orientação de TCC" }));
    await user.click(await screen.findByRole("button", { name: "Confirmar" }));
    expect(await screen.findByText("Informe a justificativa.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await user.type(screen.getByLabelText("Justificativa"), "Sem comprovação");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    await screen.findByRole("button", { name: "Nova atividade" });
    const post = calls.find((c) => c.method === "POST")!;
    expect(post.path).toBe("/api/activities/a1/status");
    expect(JSON.parse(post.init!.body as string)).toEqual({
      status: "REJEITADA",
      expected_version: 3,
      justificativa: "Sem comprovação",
    });
  });

  it("marcar como distinta chama o endpoint distinct com justificativa", async () => {
    const { calls } = mockFetch({
      ...baseRoutes(() => result("40.00", [ROW])),
      "GET /api/activities/a1": { status: 200, body: ACTIVITY },
      "POST /api/activities/a1/distinct": { status: 200, body: ACTIVITY },
    });
    renderPage();
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Marcar como distinta Orientação de TCC" }));
    await user.type(await screen.findByLabelText("Justificativa"), "Turmas diferentes");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));
    await screen.findByRole("button", { name: "Nova atividade" });
    const post = calls.find((c) => c.method === "POST")!;
    expect(post.path).toBe("/api/activities/a1/distinct");
    expect(JSON.parse(post.init!.body as string)).toEqual({ expected_version: 3, justificativa: "Turmas diferentes" });
  });

  it("TELA-06: sem tabela escolhida exibe a sugestão e pede confirmação antes de calcular", async () => {
    const { calls } = mockFetch({
      ...baseRoutes(() => result("0.00", [])),
      "GET /api/processes/proc-1/scoring/table": { status: 200, body: { chosen: null, suggested: CHOSEN, alerts: [] } },
    });
    renderPage();
    expect(await screen.findByRole("heading", { name: "Tabela sugerida" })).toBeInTheDocument();
    expect(screen.getByText("Pendente de validação")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar tabela e calcular" })).toBeInTheDocument();
    expect(calls.some((c) => c.method === "PUT")).toBe(false);
  });

  it("exibe o erro quando o carregamento falha", async () => {
    mockFetch({
      ...baseRoutes(() => result("0.00", [])),
      "GET /api/processes/proc-1/scoring/table": { status: 404, body: { detail: "Processo não encontrado" } },
    });
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Processo não encontrado");
  });

  describe("TELA-01/02: Grupo I em horas de PIT", () => {
    const PIT_ROW = (id: string, title: string, hours: string): ScoringResult["rows"][number] => ({
      ...ROW,
      activity_id: id,
      title,
      group_number: 1,
      item_number: 1,
      unit_points: null,
      effective_quantity: null,
      formula_text: null,
      points: "0.00",
      pit_hours: hours,
      alerts: [],
    });
    const WEEKLY_LOAD = {
      group_number: 1, item_number: 1, description: "Aulas Efetivas em Curso de Graduação", unit_label: "horas (PIT)", mode: "CARGA_SEMANAL" as const,
      unit_points: null, hours_per_block: null, weeks_per_semester: 17, prep_ratio: "1.00", min_hours: null, max_points: null, accepted_evidence: null, rules: null, review_note: null,
    };
    const OFFICIAL_VERSION = {
      ...VERSION,
      groups: [{ ...VERSION.groups[0], number: 1, name: "Docência", counts_in_total: false, criteria: [WEEKLY_LOAD] }, VERSION.groups[1]],
    };
    const official = (): ScoringResult => ({
      ...result("40.00", [PIT_ROW("p1", "Cálculo I", "8.00"), PIT_ROW("p2", "Álgebra", "4.00"), ROW]),
      group1_hours_by_period: { "2023.1": "12.00" },
      group1_total_hours: "12.00",
    });

    it("mostra o Grupo I em horas de PIT na tabela, sem pontos", async () => {
      mockFetch({ ...baseRoutes(official), "GET /api/scoring-versions/v-fasi": { status: 200, body: OFFICIAL_VERSION } });
      renderPage();
      const row = (await screen.findByText("Cálculo I", { selector: "td" })).closest("tr")!;
      expect(row).toHaveTextContent("8,00 horas (PIT)");
      expect(screen.getByText("Álgebra", { selector: "td" }).closest("tr")).toHaveTextContent("4,00 horas (PIT)");
      const head = screen.getByText(/Grupo I · Docência/, { selector: "th" });
      expect(head).toHaveTextContent("Total de horas (PIT): 12,00");
      expect(head).not.toHaveTextContent("Subtotal");
    });

    it("mostra o resumo com 'Total geral (Grupos II a VIII)' e as horas de PIT à parte", async () => {
      mockFetch({ ...baseRoutes(official), "GET /api/scoring-versions/v-fasi": { status: 200, body: OFFICIAL_VERSION } });
      renderPage();
      expect((await screen.findByText("Total geral (Grupos II a VIII)", { selector: "dt" })).nextElementSibling).toHaveTextContent("40,00");
      const hours = screen.getByRole("group", { name: "Horas de PIT do Grupo I" });
      expect(within(hours).getByText("PIT 2023.1", { selector: "dt" }).nextElementSibling).toHaveTextContent("12,00 horas");
      expect(within(hours).getByText("Total de horas de PIT", { selector: "dt" }).nextElementSibling).toHaveTextContent("12,00 horas");
    });

    it("com a versão que tira o Grupo I do total e nenhum lançamento, mostra 0,00 hora", async () => {
      mockFetch({
        ...baseRoutes(() => result("40.00", [ROW])),
        "GET /api/scoring-versions/v-fasi": { status: 200, body: OFFICIAL_VERSION },
      });
      renderPage();
      expect(await screen.findByText("Total geral (Grupos II a VIII)", { selector: "dt" })).toBeInTheDocument();
      const hours = screen.getByRole("group", { name: "Horas de PIT do Grupo I" });
      expect(within(hours).getByText("Total de horas de PIT", { selector: "dt" }).nextElementSibling).toHaveTextContent("0,00 horas");
    });

    it("com Grupo I fora do total mas sem carga semanal (tipo IFCH), não mostra as horas de PIT", async () => {
      const informed = { ...WEEKLY_LOAD, mode: "VALOR_INFORMADO" as const, unit_label: "pontos", weeks_per_semester: null, prep_ratio: null };
      const IFCH_VERSION = {
        ...VERSION,
        groups: [{ ...VERSION.groups[0], number: 1, name: "Docência", counts_in_total: false, criteria: [informed] }, VERSION.groups[1]],
      };
      mockFetch({
        ...baseRoutes(() => result("40.00", [ROW])),
        "GET /api/scoring-versions/v-fasi": { status: 200, body: IFCH_VERSION },
      });
      renderPage();
      expect(await screen.findByText("Total geral", { selector: "dt" })).toBeInTheDocument();
      expect(screen.queryByRole("group", { name: "Horas de PIT do Grupo I" })).not.toBeInTheDocument();
      expect(screen.queryByText("Total de horas de PIT")).not.toBeInTheDocument();
    });

    it("explica em português o alerta CARGA_HORARIA_NAO_INFORMADA e a razão CARGA_HORARIA_INSUFICIENTE", async () => {
      const course: ScoringResult["rows"][number] = {
        ...ROW,
        activity_id: "c1",
        title: "Curso de extensão",
        group_number: 4,
        item_number: 4,
        status: "NAO_PONTUADA",
        points: "0.00",
        reasons: ["CARGA_HORARIA_INSUFICIENTE"],
        alerts: [
          { code: "CARGA_HORARIA_NAO_INFORMADA", severity: "ALERTA", message: "Informe as horas do curso", norm_reference: "Tabela oficial, IV.4" },
        ],
      };
      mockFetch(baseRoutes(() => result("0.00", [course])));
      renderPage();
      expect((await screen.findByText("Curso de extensão", { selector: "td" })).closest("tr")).toHaveTextContent(
        "Carga horária abaixo do mínimo do item",
      );
      const alerta = screen.getByRole("region", { name: "Alerta (2)" });
      expect(alerta).toHaveTextContent("Carga horária não informada");
      expect(alerta).toHaveTextContent("Curso de extensão: Informe as horas do curso");
    });
  });
});
