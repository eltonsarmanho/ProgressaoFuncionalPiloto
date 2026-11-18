import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, Criterion } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ScoreEditor } from "./ScoreEditor";

const CRITERION = (mode: Criterion["mode"]): Criterion => ({
  group_number: 2,
  item_number: 7,
  description: "Orientação de TCC",
  unit_label: "orientação",
  mode,
  unit_points: "5.00",
  hours_per_block: null,
  weeks_per_semester: null,
  prep_ratio: null,
  min_hours: null,
  max_points: null,
  accepted_evidence: null,
  rules: null,
  review_note: null,
});

const ACTIVITY: Activity = {
  id: "a1",
  process_id: "p1",
  title: "Orientação de TCC de Maria",
  group_number: 2,
  item_number: 7,
  description: "",
  event_date: "2023-05-10",
  period_start: null,
  period_end: null,
  period_precision: "DAY",
  academic_period: null,
  level: null,
  quantidade: "3.00",
  horas: null,
  course_hours: null,
  informed_points: null,
  points_override: null,
  unit_points_override: null,
  evidence_note: "Declaração",
  source: "MANUAL",
  status: "VALIDADA",
  distinct_justification: null,
  candidates: [],
  version: 3,
};

function setup(over: { activity?: Partial<Activity>; mode?: Criterion["mode"]; pit?: boolean; routes?: Parameters<typeof mockFetch>[0] } = {}) {
  setCsrfToken("tok");
  const mock = mockFetch(over.routes ?? { "PUT /api/activities/a1": { status: 200, body: { ...ACTIVITY, version: 4 } } });
  const onSaved = vi.fn();
  const onCancel = vi.fn();
  render(
    <ScoreEditor
      activity={{ ...ACTIVITY, ...over.activity }}
      criterion={CRITERION(over.mode ?? "POR_UNIDADE")}
      pit={over.pit ?? false}
      onSaved={onSaved}
      onCancel={onCancel}
    />,
  );
  return { ...mock, onSaved, onCancel, user: userEvent.setup() };
}

const body = (init: RequestInit | undefined) => JSON.parse(init?.body as string);

describe("UIM-22: editor do valor unitário", () => {
  it("mostra o valor unitário da tabela e salva o digitado no PUT da atividade, sem justificativa", async () => {
    const { calls, onSaved, user } = setup();
    const field = screen.getByLabelText("Valor unitário");
    expect(field).toHaveValue(5);
    expect(screen.queryByLabelText(/Justificativa/)).not.toBeInTheDocument();

    await user.clear(field);
    await user.type(field, "2.5");
    await user.click(screen.getByRole("button", { name: "Salvar valor" }));

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    const sent = body(calls[0].init);
    expect(calls[0].path).toBe("/api/activities/a1");
    expect(sent).toMatchObject({
      title: "Orientação de TCC de Maria",
      group_number: 2,
      item_number: 7,
      quantidade: 3,
      event_date: "2023-05-10",
      evidence_note: "Declaração",
      unit_points_override: 2.5,
      expected_version: 3,
    });
    expect(sent).not.toHaveProperty("justificativa");
  });

  it("com valor já digitado, o campo vem preenchido com ele e Usar valor da tabela envia o campo vazio", async () => {
    const { calls, onSaved, user } = setup({ activity: { unit_points_override: "2.50" } });
    expect(screen.getByLabelText("Valor unitário")).toHaveValue(2.5);

    await user.click(screen.getByRole("button", { name: "Usar valor da tabela" }));

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init).unit_points_override).toBeNull();
    expect(body(calls[0].init).quantidade).toBe(3);
  });

  it("sem valor digitado não há botão Usar valor da tabela", () => {
    setup();
    expect(screen.queryByRole("button", { name: "Usar valor da tabela" })).not.toBeInTheDocument();
  });

  it("o 422 de unit_points_override aparece junto do campo e nada é salvo", async () => {
    const { onSaved, user } = setup({
      routes: { "PUT /api/activities/a1": { status: 422, body: { detail: [{ field: "unit_points_override", message: "Valor unitário deve estar entre 0 e 10000" }] } } },
    });
    await user.click(screen.getByRole("button", { name: "Salvar valor" }));
    const message = await screen.findByText("Valor unitário deve estar entre 0 e 10000");
    expect(message).toHaveAttribute("id", "unit_points_override-error");
    expect(screen.getByLabelText("Valor unitário")).toHaveAttribute("aria-describedby", "unit_points_override-error");
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("por bloco de horas também oferece o campo", () => {
    setup({ mode: "POR_BLOCO_DE_HORAS" });
    expect(screen.getByLabelText("Valor unitário")).toBeInTheDocument();
  });

  it.each([
    ["CARGA_SEMANAL", false, /carga semanal da tabela/],
    ["CARGA_SEMANAL", true, /horas de PIT/],
    ["VALOR_INFORMADO", false, /pontos informados na edição da atividade/],
  ] as const)("em %s (PIT: %s) não oferece o campo e explica numa nota curta", (mode, pit, note) => {
    setup({ mode, pit });
    expect(screen.queryByLabelText("Valor unitário")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar valor" })).not.toBeInTheDocument();
    expect(screen.getByText(note)).toBeInTheDocument();
  });

  it("Cancelar chama onCancel sem chamar a API", async () => {
    const { calls, onCancel, user } = setup();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(calls).toHaveLength(0);
  });
});
