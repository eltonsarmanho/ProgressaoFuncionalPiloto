import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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
  { code: "INTERSTICIO_INSUFICIENTE", severity: "ERRO", message: "Interstício de 14 meses; o mínimo exigido é de 24 meses.", norm_reference: "Res. 4.644/2015-CONSEPE, arts. 2º, 4º e 5º" },
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
    expect(erroItems[0]).toHaveTextContent("INTERSTICIO_INSUFICIENTE");
    expect(erroItems[0]).toHaveTextContent("Interstício de 14 meses; o mínimo exigido é de 24 meses.");
    expect(erroItems[0]).toHaveTextContent(
      "Referência normativa: Res. 4.644/2015-CONSEPE, arts. 2º, 4º e 5º",
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

  it("UI-04 / TELA-01: exibe as 9 etapas com a Etapa 1 ativa, as etapas 2 a 5 habilitadas e as etapas 6–9 desabilitadas e rotuladas 'em breve'", async () => {
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
    expect(steps[1]).toHaveTextContent("Etapa 2");
    expect(steps[1]).toHaveTextContent("Documentos");
    expect(steps[2]).toHaveTextContent("Etapa 3");
    expect(steps[2]).toHaveTextContent("Atividades");
    [1, 2].forEach((i) => {
      expect(steps[i]).not.toHaveTextContent("em breve");
      expect(steps[i]).not.toHaveAttribute("aria-disabled");
      expect(steps[i]).not.toHaveAttribute("aria-current");
    });
    expect(steps[3]).toHaveTextContent("Etapa 4");
    expect(steps[3]).toHaveTextContent("Pontuação");
    expect(steps[3]).not.toHaveTextContent("em breve");
    expect(steps[3]).not.toHaveAttribute("aria-disabled");
    expect(steps[3]).not.toHaveAttribute("aria-current");
    expect(steps[4]).toHaveTextContent("Etapa 5");
    expect(steps[4]).toHaveTextContent("Documentos gerados");
    expect(steps[4]).not.toHaveTextContent("em breve");
    expect(steps[4]).not.toHaveAttribute("aria-disabled");
    steps.forEach((step, i) => {
      if (i < 5) return;
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

describe("CAINI-01, CAINI-02, CAINI-05, CAINI-06: iniciar o processo na Etapa 1", () => {
  const OPEN = { name: "Iniciar processo" } as const;
  const base = {
    "GET /api/units": { status: 200, body: UNITS },
    "GET /api/professors": { status: 200, body: PROFESSORS },
  };

  it("CAINI-01: com processo em rascunho mostra o botão Iniciar processo", async () => {
    mockFetch({ ...base, "GET /api/processes/proc-1": { status: 200, body: SAVED } });
    renderAt("/processos/proc-1");
    expect(await screen.findByRole("button", OPEN)).toBeInTheDocument();
    expect(screen.getByText("Rascunho")).toBeInTheDocument();
  });

  it.each(["EM_ANDAMENTO", "CONCLUIDO", "ARQUIVADO"])("CAINI-02: com o processo %s não mostra o botão", async (status) => {
    mockFetch({ ...base, "GET /api/processes/proc-1": { status: 200, body: { ...SAVED, status } } });
    renderAt("/processos/proc-1");
    await screen.findByText("Duração do interstício: 24 meses e 730 dias");
    expect(screen.queryByRole("button", OPEN)).not.toBeInTheDocument();
  });

  it("CAINI-02: na criação de um processo novo não mostra o botão", async () => {
    mockFetch(base);
    renderAt("/processos/novo");
    await screen.findByRole("option", { name: "Maria Souza (SIAPE 1234567)" });
    expect(screen.queryByRole("button", OPEN)).not.toBeInTheDocument();
  });

  it("CAINI-05: confirmar com 200 mostra Em andamento, esconde o botão e o Salvar seguinte usa a versão devolvida, sem tocar nos campos digitados", async () => {
    const { calls } = mockFetch({
      ...base,
      "GET /api/processes/proc-1": { status: 200, body: SAVED },
      "POST /api/processes/proc-1/status": { status: 200, body: { ...SAVED, status: "EM_ANDAMENTO", version: 2 } },
      "PUT /api/processes/proc-1": { status: 200, body: { ...SAVED, status: "EM_ANDAMENTO", version: 3, notes: "Anotação digitada" } },
    });
    renderAt("/processos/proc-1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", OPEN));
    await user.type(screen.getByLabelText("Observações"), "Anotação digitada");
    await user.click(within(screen.getByRole("dialog", OPEN)).getByRole("button", { name: "Iniciar" }));

    expect(await screen.findByText("Em andamento")).toBeInTheDocument();
    expect(screen.queryByText("Rascunho")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", OPEN)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Observações")).toHaveValue("Anotação digitada");
    const post = calls.find((c) => c.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toEqual({ status: "EM_ANDAMENTO", expected_version: 1 });

    await user.type(screen.getByLabelText("Justificativa da alteração"), "Ajuste");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    await vi.waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    const put = calls.find((c) => c.method === "PUT")!;
    expect(JSON.parse(put.init!.body as string)).toMatchObject({ expected_version: 2, notes: "Anotação digitada" });
  });

  it("CAINI-06: 409 mostra a mensagem no modal e recarrega o processo com GET, e a etiqueta mostra o status devolvido", async () => {
    let reads = 0;
    const { calls } = mockFetch({
      ...base,
      "GET /api/processes/proc-1": () => {
        reads += 1;
        return { status: 200, body: reads === 1 ? SAVED : { ...SAVED, status: "EM_ANDAMENTO", version: 3 } };
      },
      "POST /api/processes/proc-1/status": { status: 409, body: { detail: "Versão desatualizada do processo." } },
    });
    renderAt("/processos/proc-1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", OPEN));
    await user.click(within(screen.getByRole("dialog", OPEN)).getByRole("button", { name: "Iniciar" }));

    expect(await within(screen.getByRole("dialog", OPEN)).findByRole("alert")).toHaveTextContent("Versão desatualizada do processo.");
    expect(await screen.findByText("Em andamento")).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "GET" && c.path === "/api/processes/proc-1")).toHaveLength(2);
  });
});
