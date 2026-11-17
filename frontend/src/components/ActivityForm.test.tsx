import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Activity, Criterion, ScoringGroup } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ActivityForm } from "./ActivityForm";

function crit(group: number, item: number, mode: Criterion["mode"], description: string): Criterion {
  return {
    group_number: group,
    item_number: item,
    description,
    unit_label: null,
    mode,
    unit_points: "10.00",
    hours_per_block: null,
    weeks_per_semester: null,
    prep_ratio: null,
    min_hours: null,
    max_points: null,
    accepted_evidence: null,
    rules: null,
    review_note: null,
  };
}

const GROUPS: ScoringGroup[] = [
  { number: 1, name: "Docência", counts_in_total: true, max_points: null, criteria: [crit(1, 1, "CARGA_SEMANAL", "Aulas na graduação"), crit(1, 2, "CARGA_SEMANAL", "Aulas na pós")] },
  { number: 2, name: "Orientação", counts_in_total: true, max_points: null, criteria: [crit(2, 7, "POR_UNIDADE", "Orientação de TCC")] },
  { number: 3, name: "Bancas", counts_in_total: true, max_points: null, criteria: [crit(3, 2, "POR_BLOCO_DE_HORAS", "Curso ministrado")] },
  { number: 8, name: "Produção", counts_in_total: true, max_points: null, criteria: [crit(8, 11, "VALOR_INFORMADO", "Artigo em periódico")] },
];

const SAVED: Activity = {
  id: "a1",
  process_id: "p1",
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

async function pick(group: string, item?: string) {
  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText("Grupo"), group);
  if (item) await user.selectOptions(screen.getByLabelText("Item"), item);
  return user;
}

describe("ActivityForm", () => {
  it("TELA-04: POR_UNIDADE mostra Quantidade e não Horas", async () => {
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={vi.fn()} />);
    await pick("2", "7");
    expect(screen.getByLabelText("Quantidade")).toBeInTheDocument();
    expect(screen.queryByLabelText("Horas")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Pontos informados")).not.toBeInTheDocument();
  });

  it("TELA-04: POR_BLOCO_DE_HORAS mostra Horas e não Quantidade", async () => {
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={vi.fn()} />);
    await pick("3", "2");
    expect(screen.getByLabelText("Horas")).toBeInTheDocument();
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
  });

  it("TELA-04: VALOR_INFORMADO mostra Pontos informados", async () => {
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={vi.fn()} />);
    await pick("8", "11");
    expect(screen.getByLabelText("Pontos informados")).toBeInTheDocument();
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
  });

  it("TELA-04: Grupo I mostra período letivo, nível, horas, carga do curso e pontuação manual", async () => {
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={vi.fn()} />);
    await pick("1");
    expect(screen.getByLabelText("Período letivo (AAAA.N)")).toBeInTheDocument();
    expect(screen.getByLabelText("Nível")).toBeInTheDocument();
    expect(screen.getByLabelText("Horas semanais")).toBeInTheDocument();
    expect(screen.getByLabelText("Carga horária do curso (opcional)")).toBeInTheDocument();
    expect(screen.getByLabelText("Pontuação manual (substitui o cálculo)")).toBeInTheDocument();
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
  });

  it("TELA-04: cria atividade com POST e devolve a atividade salva", async () => {
    const { calls } = mockFetch({
      "POST /api/processes/p1/activities": { status: 201, body: SAVED },
    });
    const onSaved = vi.fn();
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={onSaved} />);
    const user = await pick("2", "7");
    await user.type(screen.getByLabelText("Título"), "Orientação de TCC");
    await user.type(screen.getByLabelText("Data do evento ou mês (AAAA-MM-DD ou AAAA-MM)"), "2023-05");
    await user.type(screen.getByLabelText("Quantidade"), "4");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(onSaved).toHaveBeenCalledWith(SAVED);
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({
      title: "Orientação de TCC",
      event_date: "2023-05",
      group_number: 2,
      item_number: 7,
      quantidade: 4,
    });
  });

  it("TELA-04: Grupo I envia período letivo, nível e horas sem item (derivado pelo nível)", async () => {
    const { calls } = mockFetch({
      "POST /api/processes/p1/activities": { status: 201, body: SAVED },
    });
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={vi.fn()} />);
    const user = await pick("1");
    await user.type(screen.getByLabelText("Título"), "Aulas 2022.1");
    await user.type(screen.getByLabelText("Período letivo (AAAA.N)"), "2022.1");
    await user.selectOptions(screen.getByLabelText("Nível"), "GRADUACAO");
    await user.type(screen.getByLabelText("Horas semanais"), "68");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({
      title: "Aulas 2022.1",
      academic_period: "2022.1",
      level: "GRADUACAO",
      group_number: 1,
      horas: 68,
    });
  });

  it("TELA-04: na edição, sem justificativa não envia e mostra o erro junto ao campo", async () => {
    const { calls } = mockFetch({});
    render(<ActivityForm processId="p1" groups={GROUPS} activity={SAVED} onSaved={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(calls).toHaveLength(0);
    const field = screen.getByLabelText("Justificativa da alteração");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Informe a justificativa da alteração.")).toBeInTheDocument();
  });

  it("TELA-04: na edição, com justificativa envia PUT com expected_version", async () => {
    const { calls } = mockFetch({ "PUT /api/activities/a1": { status: 200, body: { ...SAVED, version: 4 } } });
    const onSaved = vi.fn();
    render(<ActivityForm processId="p1" groups={GROUPS} activity={SAVED} onSaved={onSaved} />);
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("Quantidade"));
    await user.type(screen.getByLabelText("Quantidade"), "5");
    await user.type(screen.getByLabelText("Justificativa da alteração"), "Corrigido conforme ata");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    const body = JSON.parse(calls[0].init!.body as string);
    expect(body.expected_version).toBe(3);
    expect(body.justificativa).toBe("Corrigido conforme ata");
    expect(body.quantidade).toBe(5);
    expect(onSaved).toHaveBeenCalledWith({ ...SAVED, version: 4 });
  });

  it("TELA-05: 422 mostra a mensagem junto ao campo indicado", async () => {
    mockFetch({
      "POST /api/processes/p1/activities": {
        status: 422,
        body: {
          detail: [
            { field: "quantidade", message: "Quantidade deve ser um inteiro entre 0 e 10000" },
            { field: "title", message: "Título obrigatório" },
          ],
        },
      },
    });
    const onSaved = vi.fn();
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={onSaved} />);
    const user = await pick("2", "7");
    await user.type(screen.getByLabelText("Quantidade"), "-1");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    const q = await screen.findByText("Quantidade deve ser um inteiro entre 0 e 10000");
    expect(q).toHaveAttribute("id", "quantidade-error");
    expect(screen.getByLabelText("Quantidade")).toHaveAttribute("aria-describedby", "quantidade-error");
    expect(screen.getByText("Título obrigatório")).toHaveAttribute("id", "title-error");
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("TELA-04: pontuação manual exige justificativa mesmo na criação", async () => {
    const { calls } = mockFetch({});
    render(<ActivityForm processId="p1" groups={GROUPS} onSaved={vi.fn()} />);
    const user = await pick("1");
    expect(screen.queryByLabelText("Justificativa da alteração")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Título"), "Aulas");
    await user.type(screen.getByLabelText("Pontuação manual (substitui o cálculo)"), "12");
    expect(screen.getByLabelText("Justificativa da alteração")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    expect(calls).toHaveLength(0);
    expect(screen.getByText("Informe a justificativa da alteração.")).toBeInTheDocument();
  });
});
