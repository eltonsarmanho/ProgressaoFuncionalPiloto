import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Activity, Criterion, ScoringGroup } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ActivityForm } from "./ActivityForm";

function crit(group: number, item: number, mode: Criterion["mode"], description: string, over: Partial<Criterion> = {}): Criterion {
  return {
    group_number: group, item_number: item, description, unit_label: "unidade", mode, unit_points: "10.00", hours_per_block: null,
    weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null, accepted_evidence: null, rules: null, review_note: null, ...over,
  };
}

const GROUPS: ScoringGroup[] = [
  { number: 1, name: "Docência", counts_in_total: true, max_points: null, criteria: [crit(1, 1, "CARGA_SEMANAL", "Aulas na graduação"), crit(1, 2, "CARGA_SEMANAL", "Aulas na pós")] },
  {
    number: 2, name: "Orientação", counts_in_total: true, max_points: null,
    criteria: [
      crit(2, 7, "POR_UNIDADE", "Orientação de TCC"),
      crit(2, 9, "POR_UNIDADE", "Coordenação de projeto", { unit_label: "por ano de coordenação" }),
    ],
  },
  { number: 3, name: "Bancas", counts_in_total: true, max_points: null, criteria: [crit(3, 2, "POR_BLOCO_DE_HORAS", "Curso ministrado", { min_hours: "20.00" })] },
];

const SAVED: Activity = {
  id: "a1", process_id: "p1", title: "Orientação de TCC", group_number: 2, item_number: 7, description: "Orientou a aluna X",
  event_date: "2023-05-10", period_start: null, period_end: null, period_precision: "DAY", academic_period: null, level: null,
  quantidade: "4.00", horas: "30.00", course_hours: "60.00", informed_points: "3.00", points_override: "9.00", evidence_note: "Declaração",
  source: "MANUAL", status: "VALIDADA", distinct_justification: null, candidates: [], version: 3,
};

const OFFERING: Activity = {
  ...SAVED, id: "g1", title: "Aulas 2022.1", group_number: 1, item_number: 1, event_date: null, quantidade: null, horas: "68.00",
  academic_period: "2022.1", level: "GRADUACAO", course_hours: null, informed_points: null, points_override: null,
};

const sent = (init: RequestInit | undefined) => JSON.parse(init?.body as string);
const noField = (label: string | RegExp) => expect(screen.queryByLabelText(label)).not.toBeInTheDocument();

function edit(a: Activity, routes: Parameters<typeof mockFetch>[0] = { [`PUT /api/activities/${a.id}`]: { status: 200, body: { ...a, version: a.version + 1 } } }) {
  const mock = mockFetch(routes);
  const onSaved = vi.fn();
  render(<ActivityForm processId="p1" groups={GROUPS} activity={a} onSaved={onSaved} />);
  return { ...mock, onSaved, user: userEvent.setup() };
}

function create(routes: Parameters<typeof mockFetch>[0] = { "POST /api/processes/p1/activities": { status: 201, body: SAVED } }) {
  const mock = mockFetch(routes);
  const onSaved = vi.fn();
  render(<ActivityForm processId="p1" groups={GROUPS} onSaved={onSaved} />);
  return { ...mock, onSaved, user: userEvent.setup() };
}

describe("EDT-01: campos da edição", () => {
  it("categoria comum: Título, Data e Categoria, e nada mais", () => {
    edit(SAVED);
    expect(screen.getByLabelText("Título")).toHaveValue("Orientação de TCC");
    expect(screen.getByLabelText("Data")).toHaveValue("2023-05-10");
    expect(screen.getByLabelText("Categoria")).toHaveValue("2.7");
    for (const gone of ["Descrição", "Comprovante", "Quantidade", "Horas", "Início", "Fim", "Pontos informados", "Pontuação manual (substitui o cálculo)", "Grupo", "Item", /Justificativa/]) noField(gone);
  });

  it("categoria medida por ano: Início e Fim no lugar da Data", () => {
    edit({ ...SAVED, item_number: 9, event_date: null, period_start: "2023-01-01", period_end: "2023-12-31" });
    expect(screen.getByLabelText("Início")).toHaveValue("2023-01-01");
    expect(screen.getByLabelText("Fim")).toHaveValue("2023-12-31");
    noField("Data");
  });

  it("Horas só aparecem quando a categoria tem carga horária mínima", () => {
    edit({ ...SAVED, group_number: 3, item_number: 2 });
    expect(screen.getByLabelText("Horas")).toHaveValue(30);
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
  });

  it("trocar a categoria troca os campos que o formulário mostra", async () => {
    const { user } = edit(SAVED);
    noField("Horas");
    await user.selectOptions(screen.getByLabelText("Categoria"), "3.2");
    expect(screen.getByLabelText("Horas")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Categoria"), "2.9");
    expect(screen.getByLabelText("Início")).toBeInTheDocument();
    noField("Horas");
  });

  it("EDT-05: oferta do Grupo I mostra só Título e Categoria", () => {
    edit(OFFERING);
    expect(screen.getByLabelText("Título")).toHaveValue("Aulas 2022.1");
    expect(screen.getByLabelText("Categoria")).toBeInTheDocument();
    for (const gone of ["Data", "Início", "Fim", "Horas", "Horas semanais", "Quantidade", "Nível", /Período letivo/]) noField(gone);
    expect(screen.getByText(/o período letivo, o nível e as horas vêm do documento/)).toBeInTheDocument();
  });

  it("sem tabela escolhida a Categoria pede para escolher a tabela", () => {
    render(<ActivityForm processId="p1" groups={[]} activity={SAVED} onSaved={vi.fn()} />);
    expect(screen.getByText(/Escolha a tabela de pontuação/)).toBeInTheDocument();
  });
});

describe("EDT-06, EDT-07: salvar na hora, o corpo completo, sem comprovante", () => {
  it("salvar manda o corpo completo e mantém o que não foi editado, com expected_version e sem justificativa", async () => {
    const { calls, onSaved, user } = edit({ ...SAVED, unit_points_override: "2.50", candidates: [{ group_number: 4, item_number: 1, justification: "" }] });
    await user.clear(screen.getByLabelText("Título"));
    await user.type(screen.getByLabelText("Título"), "Orientação corrigida");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(calls[0].path).toBe("/api/activities/a1");
    expect(sent(calls[0].init)).toEqual({
      title: "Orientação corrigida", description: "Orientou a aluna X", group_number: 2, item_number: 7, event_date: "2023-05-10",
      evidence_note: "Declaração", quantidade: 4, horas: 30, course_hours: 60, informed_points: 3, points_override: 9,
      unit_points_override: 2.5, candidates: [{ group_number: 4, item_number: 1, justification: "" }], expected_version: 3,
    });
    expect(sent(calls[0].init)).not.toHaveProperty("justificativa");
  });

  it("não há campo de justificativa nem de comprovante, e salvar não abre painel", async () => {
    const { user } = edit(SAVED);
    noField(/justificativa/i);
    noField(/comprovante/i);
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("trocar a categoria manda o grupo e o item novos; trocar a data manda a nova", async () => {
    const { calls, user } = edit(SAVED);
    await user.selectOptions(screen.getByLabelText("Categoria"), "3.2");
    await user.clear(screen.getByLabelText("Data"));
    await user.type(screen.getByLabelText("Data"), "2024-02");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(sent(calls[0].init)).toMatchObject({ group_number: 3, item_number: 2, event_date: "2024-02", quantidade: 4, horas: 30 });
  });

  it("esvaziar a data tira a data do corpo", async () => {
    const { calls, user } = edit(SAVED);
    await user.clear(screen.getByLabelText("Data"));
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(sent(calls[0].init)).not.toHaveProperty("event_date");
  });

  it("categoria por ano: salvar manda o período e tira a data do evento", async () => {
    const { calls, user } = edit({ ...SAVED, item_number: 9 });
    await user.type(screen.getByLabelText("Início"), "2023-01-01");
    await user.type(screen.getByLabelText("Fim"), "2023-12-31");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    const body = sent(calls[0].init);
    expect(body).toMatchObject({ period_start: "2023-01-01", period_end: "2023-12-31" });
    expect(body).not.toHaveProperty("event_date");
  });

  it("categoria por ano sem período digitado mantém a data do evento que a atividade já tinha", async () => {
    const { calls, user } = edit({ ...SAVED, item_number: 9 });
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(sent(calls[0].init).event_date).toBe("2023-05-10");
  });

  it("a oferta do Grupo I salva o corpo completo, com período letivo, nível e horas intactos", async () => {
    const { calls, user } = edit(OFFERING);
    await user.clear(screen.getByLabelText("Título"));
    await user.type(screen.getByLabelText("Título"), "Aulas 2022.1 (corrigido)");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(sent(calls[0].init)).toMatchObject({
      title: "Aulas 2022.1 (corrigido)", group_number: 1, item_number: 1, academic_period: "2022.1", level: "GRADUACAO", horas: 68, expected_version: 3,
    });
  });

  it("editar Horas (com carga mínima) manda o valor novo", async () => {
    const { calls, user } = edit({ ...SAVED, group_number: 3, item_number: 2 });
    await user.clear(screen.getByLabelText("Horas"));
    await user.type(screen.getByLabelText("Horas"), "12");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(sent(calls[0].init).horas).toBe(12);
  });
});

describe("EDT-04: atividade nova", () => {
  it("pede Título, Data, Categoria e Quantidade", () => {
    create();
    for (const label of ["Título", "Data", "Categoria", "Quantidade"]) expect(screen.getByLabelText(label)).toBeInTheDocument();
    for (const gone of ["Descrição", "Comprovante", "Horas", "Pontos informados", /Justificativa/]) noField(gone);
  });

  it("cria com POST, só com o que foi preenchido, e devolve a atividade salva", async () => {
    const { calls, onSaved, user } = create();
    await user.type(screen.getByLabelText("Título"), "Orientação de TCC");
    await user.type(screen.getByLabelText("Data"), "2023-05");
    await user.selectOptions(screen.getByLabelText("Categoria"), "2.7");
    await user.type(screen.getByLabelText("Quantidade"), "4");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledWith(SAVED));
    expect(calls[0].method).toBe("POST");
    expect(sent(calls[0].init)).toEqual({ title: "Orientação de TCC", event_date: "2023-05", group_number: 2, item_number: 7, quantidade: 4 });
  });

  it("com categoria de carga mínima pede também as Horas", async () => {
    const { user } = create();
    await user.selectOptions(screen.getByLabelText("Categoria"), "3.2");
    expect(screen.getByLabelText("Horas")).toBeInTheDocument();
  });

  it("Grupo I novo pede período letivo, nível e horas semanais, sem Data nem Quantidade, e não manda item", async () => {
    const { calls, user } = create();
    await user.selectOptions(screen.getByLabelText("Categoria"), "1.1");
    for (const gone of ["Data", "Quantidade"]) noField(gone);
    await user.type(screen.getByLabelText("Título"), "Aulas 2022.1");
    await user.type(screen.getByLabelText(/Período letivo/), "2022.1");
    await user.selectOptions(screen.getByLabelText("Nível"), "GRADUACAO");
    await user.type(screen.getByLabelText("Horas semanais"), "68");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(sent(calls[0].init)).toEqual({ title: "Aulas 2022.1", group_number: 1, academic_period: "2022.1", level: "GRADUACAO", horas: 68 });
  });

  it("TELA-05: 422 mostra a mensagem junto ao campo indicado e não salva", async () => {
    const { onSaved, user } = create({
      "POST /api/processes/p1/activities": {
        status: 422,
        body: { detail: [{ field: "quantidade", message: "Quantidade deve ser um inteiro entre 0 e 10000" }, { field: "title", message: "Título obrigatório" }] },
      },
    });
    await user.type(screen.getByLabelText("Quantidade"), "-1");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    const q = await screen.findByText("Quantidade deve ser um inteiro entre 0 e 10000");
    expect(q).toHaveAttribute("id", "quantidade-error");
    expect(screen.getByLabelText("Quantidade")).toHaveAttribute("aria-describedby", "quantidade-error");
    expect(screen.getByText("Título obrigatório")).toHaveAttribute("id", "title-error");
    expect(onSaved).not.toHaveBeenCalled();
  });
});

describe("EDT-02, EDT-03: erros de data no formulário", () => {
  const RANGE = "A data deve estar entre 01/01/2024 e 31/12/2025";
  const issue = (field: string, message = RANGE) => ({ status: 422, body: { detail: [{ field, code: "VALIDACAO", message }] } });

  it("422 em event_date mostra a faixa no campo da data, ligada a ele, com o foco nele", async () => {
    const { onSaved, user } = edit(SAVED, { "PUT /api/activities/a1": issue("event_date") });
    await user.clear(screen.getByLabelText("Data"));
    await user.type(screen.getByLabelText("Data"), "2023-03-15");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    const message = await screen.findByText(RANGE);
    expect(message).toHaveAttribute("id", "event_date-error");
    expect(screen.getByLabelText("Data")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Data").getAttribute("aria-describedby")).toContain("event_date-error");
    expect(screen.getByLabelText("Data")).toHaveFocus();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("o formulário não fecha nem perde o que foi digitado depois do erro", async () => {
    const { user } = edit(SAVED, { "PUT /api/activities/a1": issue("event_date") });
    await user.clear(screen.getByLabelText("Título"));
    await user.type(screen.getByLabelText("Título"), "Título novo");
    await user.clear(screen.getByLabelText("Data"));
    await user.type(screen.getByLabelText("Data"), "2023-03-15");
    await user.selectOptions(screen.getByLabelText("Categoria"), "3.2");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await screen.findByText(RANGE);
    expect(screen.getByRole("form", { name: "Editar atividade" })).toBeInTheDocument();
    expect(screen.getByLabelText("Título")).toHaveValue("Título novo");
    expect(screen.getByLabelText("Data")).toHaveValue("2023-03-15");
    expect(screen.getByLabelText("Categoria")).toHaveValue("3.2");
    expect(screen.getByRole("button", { name: "Salvar atividade" })).toBeEnabled();
  });

  it("422 em period_start ou period_end mostra a faixa no campo do período", async () => {
    const { user } = edit({ ...SAVED, item_number: 9 }, {
      "PUT /api/activities/a1": {
        status: 422,
        body: { detail: [{ field: "period_start", message: RANGE }, { field: "period_end", message: "A data deve estar entre 01/01/2024 e 31/12/2025" }] },
      },
    });
    await user.type(screen.getByLabelText("Início"), "2021-01-01");
    await user.type(screen.getByLabelText("Fim"), "2021-12-31");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await screen.findAllByText(RANGE);
    expect(document.getElementById("period_start-error")).toHaveTextContent(RANGE);
    expect(document.getElementById("period_end-error")).toHaveTextContent(RANGE);
    expect(screen.getByLabelText("Início")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Início")).toHaveValue("2021-01-01");
    expect(screen.getByLabelText("Início")).toHaveFocus();
  });

  it("corrigir a data e salvar de novo limpa o erro", async () => {
    let fail = true;
    const { onSaved, user } = edit(SAVED, {
      "PUT /api/activities/a1": () => (fail ? issue("event_date") : { status: 200, body: SAVED }),
    });
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await screen.findByText(RANGE);
    fail = false;
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(screen.queryByText(RANGE)).not.toBeInTheDocument();
  });

  it("422 em campo que o formulário não mostra aparece como alerta, sem sumir", async () => {
    const { user } = edit(OFFERING, { "PUT /api/activities/g1": issue("academic_period", "Período letivo deve ser AAAA.N") });
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Período letivo deve ser AAAA.N");
  });

  it("409 mostra a mensagem de versão alterada e mantém o formulário aberto", async () => {
    const { onSaved, user } = edit(SAVED, { "PUT /api/activities/a1": { status: 409, body: { detail: "A atividade foi alterada; recarregue" } } });
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A atividade foi alterada; recarregue");
    expect(screen.getByRole("form", { name: "Editar atividade" })).toBeInTheDocument();
    expect(onSaved).not.toHaveBeenCalled();
  });
});
