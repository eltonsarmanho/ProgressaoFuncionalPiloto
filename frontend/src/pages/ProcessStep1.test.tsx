import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { ProcessStep1 } from "./ProcessStep1";
import { mockFetch } from "../test/fetchMock";

const UNITS = [
  { id: "u-fasi", name: "Faculdade de Sistemas de Informação", acronym: "FASI", kind: "FACULDADE", parent_id: null, archived: false },
];
const PROFESSORS = [
  { id: "p1", full_name: "Maria Souza", siape: "1234567", titration: "DOUTORADO", position: "Professor", career: "MAGISTERIO_SUPERIOR", unit_id: "u-fasi", faculty: "FASI", campus: "Cametá", work_regime: "DE", archived: false, version: 1 },
];

const ALERTS = [
  { code: "MODALIDADE_INCOMPATIVEL", severity: "ERRO", message: "Modalidade incompatível com as classes informadas", norm_reference: "Res. 4.644/2015-CONSEPE, art. 1º, parágrafo único; Lei 12.772/2012, art. 12" },
  { code: "INTERSTICIO_NAO_CONCLUIDO", severity: "ALERTA", message: "A data final é posterior à data de abertura", norm_reference: "Res. 4.644/2015-CONSEPE, art. 29" },
  { code: "CLASSE_INEXISTENTE_NA_ESTRUTURA", severity: "ERRO", message: "Nível 4 não existe na Classe D", norm_reference: "Lei 12.772/2012, Anexo I" },
  { code: "INTERSTICIO_CRUZA_REESTRUTURACAO", severity: "REQUER_ANALISE_NORMATIVA", message: "O interstício cruza 01/01/2025", norm_reference: "Lei 15.141/2025 (Lei 12.772/2012, art. 12, §7º, e Anexo II)" },
];

const SAVED = {
  id: "proc-1",
  professor_id: "p1",
  unit_id: "u-fasi",
  modality: "PROMOCAO",
  current_class: "D",
  current_denomination: "Associado",
  current_level: 4,
  target_class: "D",
  target_denomination: "Associado",
  target_level: 2,
  start_date: "2024-11-23",
  end_date: "2026-11-23",
  opening_date: "2026-11-16",
  notes: null,
  resp_name: null,
  resp_position: null,
  resp_appointment: null,
  resp_admin_unit: null,
  status: "RASCUNHO",
  version: 1,
  created_at: "2026-11-16T10:00:00Z",
  updated_at: "2026-11-16T10:00:00Z",
  interstice: { months: 24, days: 730 },
  alerts: ALERTS,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/processos/novo" element={<ProcessStep1 />} />
        <Route path="/processos/:id" element={<ProcessStep1 />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProcessStep1", () => {
  it("UI-03: após salvar exibe a duração do interstício e os alertas agrupados por severidade com referência normativa", async () => {
    const { calls } = mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "GET /api/professors": { status: 200, body: PROFESSORS },
      "POST /api/processes": { status: 201, body: SAVED },
    });
    renderAt("/processos/novo");
    const user = userEvent.setup();
    await screen.findByRole("option", { name: "Maria Souza (SIAPE 1234567)" });
    await user.selectOptions(screen.getByLabelText("Docente"), "p1");
    await user.selectOptions(screen.getByLabelText("Modalidade"), "PROMOCAO");
    await user.type(screen.getByLabelText("Classe atual"), "D");
    await user.type(screen.getByLabelText("Denominação atual"), "Associado");
    await user.type(screen.getByLabelText("Nível atual"), "4");
    await user.type(screen.getByLabelText("Classe pretendida"), "D");
    await user.type(screen.getByLabelText("Denominação pretendida"), "Associado");
    await user.type(screen.getByLabelText("Nível pretendido"), "2");
    await user.type(screen.getByLabelText("Data inicial do interstício"), "2024-11-23");
    await user.type(screen.getByLabelText("Data final do interstício"), "2026-11-23");
    await user.type(screen.getByLabelText("Data de abertura"), "2026-11-16");
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    const result = await screen.findByRole("region", { name: "Resultado da verificação" });
    expect(within(result).getByText("Duração do interstício: 24 meses e 730 dias")).toBeInTheDocument();

    const erro = within(result).getByRole("region", { name: "Erro (2)" });
    const erroItems = within(erro).getAllByRole("listitem");
    expect(erroItems).toHaveLength(2);
    expect(erroItems[0]).toHaveTextContent("MODALIDADE_INCOMPATIVEL");
    expect(erroItems[0]).toHaveTextContent("Modalidade incompatível com as classes informadas");
    expect(erroItems[0]).toHaveTextContent(
      "Referência normativa: Res. 4.644/2015-CONSEPE, art. 1º, parágrafo único; Lei 12.772/2012, art. 12",
    );
    expect(erroItems[1]).toHaveTextContent("CLASSE_INEXISTENTE_NA_ESTRUTURA");
    expect(erroItems[1]).toHaveTextContent("Referência normativa: Lei 12.772/2012, Anexo I");

    const alerta = within(result).getByRole("region", { name: "Alerta (1)" });
    expect(within(alerta).getAllByRole("listitem")).toHaveLength(1);
    expect(alerta).toHaveTextContent("INTERSTICIO_NAO_CONCLUIDO");
    expect(alerta).toHaveTextContent("Referência normativa: Res. 4.644/2015-CONSEPE, art. 29");

    const analise = within(result).getByRole("region", { name: "Requer análise normativa (1)" });
    expect(within(analise).getAllByRole("listitem")).toHaveLength(1);
    expect(analise).toHaveTextContent("INTERSTICIO_CRUZA_REESTRUTURACAO");
    expect(analise).toHaveTextContent(
      "Referência normativa: Lei 15.141/2025 (Lei 12.772/2012, art. 12, §7º, e Anexo II)",
    );

    const post = calls.find((c) => c.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toEqual({
      professor_id: "p1",
      unit_id: "u-fasi",
      modality: "PROMOCAO",
      current_class: "D",
      current_denomination: "Associado",
      current_level: 4,
      target_class: "D",
      target_denomination: "Associado",
      target_level: 2,
      start_date: "2024-11-23",
      end_date: "2026-11-23",
      opening_date: "2026-11-16",
      notes: null,
      resp_name: null,
      resp_position: null,
      resp_appointment: null,
      resp_admin_unit: null,
    });
  });

  it("UI-04 / TELA-01: exibe as 9 etapas com a Etapa 1 ativa, a Etapa 4 habilitada e as etapas 2, 3 e 5–9 desabilitadas e rotuladas 'em breve'", async () => {
    mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "GET /api/professors": { status: 200, body: PROFESSORS },
    });
    renderAt("/processos/novo");
    const nav = await screen.findByRole("navigation", { name: "Etapas do processo" });
    const steps = within(nav).getAllByRole("listitem");
    expect(steps).toHaveLength(9);
    expect(steps[0]).toHaveAttribute("aria-current", "step");
    expect(steps[0]).not.toHaveTextContent("em breve");
    expect(steps[0]).not.toHaveAttribute("aria-disabled");
    expect(steps[3]).toHaveTextContent("Etapa 4");
    expect(steps[3]).toHaveTextContent("Pontuação");
    expect(steps[3]).not.toHaveTextContent("em breve");
    expect(steps[3]).not.toHaveAttribute("aria-disabled");
    expect(steps[3]).not.toHaveAttribute("aria-current");
    steps.forEach((step, i) => {
      if (i === 0 || i === 3) return;
      expect(step).toHaveTextContent(`Etapa ${i + 1}`);
      expect(step).toHaveTextContent("em breve");
      expect(step).toHaveAttribute("aria-disabled", "true");
      expect(step).not.toHaveAttribute("aria-current");
      expect(within(step).queryByRole("link")).not.toBeInTheDocument();
    });
  });

  it("TELA-01: com um processo aberto, Etapa 1 e Etapa 4 são links para o processo e para a pontuação", async () => {
    mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "GET /api/professors": { status: 200, body: PROFESSORS },
      "GET /api/processes/proc-1": { status: 200, body: SAVED },
    });
    renderAt("/processos/proc-1");
    const nav = await screen.findByRole("navigation", { name: "Etapas do processo" });
    const steps = within(nav).getAllByRole("listitem");
    expect(within(steps[3]).getByRole("link", { name: /Etapa 4/ })).toHaveAttribute(
      "href",
      "/processos/proc-1/pontuacao",
    );
    expect(within(steps[0]).getByRole("link", { name: /Etapa 1/ })).toHaveAttribute("href", "/processos/proc-1");
  });

  it("edição em andamento: 422 exibe a mensagem junto ao campo justificativa e PUT envia expected_version", async () => {
    const { calls } = mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "GET /api/professors": { status: 200, body: PROFESSORS },
      "GET /api/processes/proc-1": { status: 200, body: { ...SAVED, status: "EM_ANDAMENTO", version: 5 } },
      "PUT /api/processes/proc-1": {
        status: 422,
        body: { detail: [{ field: "justificativa", message: "Justificativa obrigatória para processo em andamento" }] },
      },
    });
    renderAt("/processos/proc-1");
    const user = userEvent.setup();
    const level = await screen.findByDisplayValue("2");
    expect(screen.getByText("Duração do interstício: 24 meses e 730 dias")).toBeInTheDocument();
    await user.clear(level);
    await user.type(level, "1");
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    const field = screen.getByLabelText("Justificativa da alteração");
    expect(await screen.findByText("Justificativa obrigatória para processo em andamento")).toBeInTheDocument();
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field.nextElementSibling).toHaveTextContent("Justificativa obrigatória para processo em andamento");
    const put = calls.find((c) => c.method === "PUT")!;
    expect(JSON.parse(put.init!.body as string)).toMatchObject({
      target_level: 1,
      expected_version: 5,
      justificativa: null,
    });
  });
});
