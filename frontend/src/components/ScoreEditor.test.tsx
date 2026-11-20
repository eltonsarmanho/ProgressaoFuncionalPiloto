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
    await user.click(screen.getByRole("button", { name: "Salvar pontuação" }));

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
    await user.click(screen.getByRole("button", { name: "Salvar pontuação" }));
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
    expect(screen.queryByRole("button", { name: "Salvar pontuação" })).not.toBeInTheDocument();
    expect(screen.getByText(note)).toBeInTheDocument();
  });

  it("Cancelar chama onCancel sem chamar a API", async () => {
    const { calls, onCancel, user } = setup();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(calls).toHaveLength(0);
  });
});

describe("QTD-01: Quantidade ou Horas, e o valor manual", () => {
  const submit = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: "Salvar pontuação" }));

  it("item por unidade mostra Quantidade com o valor da atividade e não mostra Horas", () => {
    setup();
    expect(screen.getByLabelText("Quantidade")).toHaveValue(3);
    expect(screen.queryByLabelText("Horas")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Valor unitário")).toBeInTheDocument();
  });

  it("item por bloco de horas mostra Horas e não mostra Quantidade", () => {
    setup({ mode: "POR_BLOCO_DE_HORAS", activity: { quantidade: null, horas: "40.00" } });
    expect(screen.getByLabelText("Horas")).toHaveValue(40);
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Valor unitário")).toBeInTheDocument();
  });

  it.each([
    ["CARGA_SEMANAL", false],
    ["CARGA_SEMANAL", true],
    ["VALOR_INFORMADO", false],
  ] as const)("em %s (PIT: %s) não oferece Quantidade nem Horas", (mode, pit) => {
    setup({ mode, pit });
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Horas")).not.toBeInTheDocument();
  });

  it("QTD-02: salvar a quantidade manda o corpo completo, sem justificativa, e avisa o pai para recarregar o total", async () => {
    const { calls, onSaved, user } = setup({ activity: { description: "Aluna X", points_override: "9.00", unit_points_override: "2.50" } });
    await user.clear(screen.getByLabelText("Quantidade"));
    await user.type(screen.getByLabelText("Quantidade"), "5");
    await submit(user);
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    const sent = body(calls[0].init);
    expect(sent).toEqual({
      title: "Orientação de TCC de Maria", description: "Aluna X", group_number: 2, item_number: 7, event_date: "2023-05-10",
      evidence_note: "Declaração", quantidade: 5, points_override: 9, unit_points_override: 2.5, expected_version: 3,
    });
    expect(screen.queryByLabelText(/Justificativa/)).not.toBeInTheDocument();
  });

  it("salvar as horas manda horas e mantém a quantidade que a atividade tinha", async () => {
    const { calls, onSaved, user } = setup({ mode: "POR_BLOCO_DE_HORAS", activity: { horas: "40.00" } });
    await user.clear(screen.getByLabelText("Horas"));
    await user.type(screen.getByLabelText("Horas"), "60");
    await submit(user);
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toMatchObject({ horas: 60, quantidade: 3, expected_version: 3 });
  });

  it("esvaziar a Quantidade tira o campo do corpo (o motor assume 1 e avisa)", async () => {
    const { calls, user } = setup();
    await user.clear(screen.getByLabelText("Quantidade"));
    await submit(user);
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(body(calls[0].init)).not.toHaveProperty("quantidade");
  });

  it("a quantidade e o valor unitário vão juntos no mesmo salvar", async () => {
    const { calls, user } = setup();
    await user.clear(screen.getByLabelText("Quantidade"));
    await user.type(screen.getByLabelText("Quantidade"), "2");
    await user.clear(screen.getByLabelText("Valor unitário"));
    await user.type(screen.getByLabelText("Valor unitário"), "7.5");
    await submit(user);
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(body(calls[0].init)).toMatchObject({ quantidade: 2, unit_points_override: 7.5 });
  });

  it("Usar valor da tabela manda o valor nulo e a quantidade digitada", async () => {
    const { calls, user } = setup({ activity: { unit_points_override: "2.50" } });
    await user.clear(screen.getByLabelText("Quantidade"));
    await user.type(screen.getByLabelText("Quantidade"), "6");
    await user.click(screen.getByRole("button", { name: "Usar valor da tabela" }));
    await vi.waitFor(() => expect(calls).toHaveLength(1));
    expect(body(calls[0].init)).toMatchObject({ unit_points_override: null, quantidade: 6 });
  });

  it("QTD-03: quantidade negativa mostra o erro do 422 no campo da quantidade e não salva", async () => {
    const { onSaved, user } = setup({
      routes: { "PUT /api/activities/a1": { status: 422, body: { detail: [{ field: "quantidade", message: "Quantidade deve ser um inteiro entre 0 e 10000" }] } } },
    });
    await user.clear(screen.getByLabelText("Quantidade"));
    await user.type(screen.getByLabelText("Quantidade"), "-1");
    await submit(user);
    const message = await screen.findByText("Quantidade deve ser um inteiro entre 0 e 10000");
    expect(message).toHaveAttribute("id", "quantidade-error");
    expect(screen.getByLabelText("Quantidade")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Quantidade")).toHaveAttribute("aria-describedby", "quantidade-error");
    expect(screen.getByLabelText("Quantidade")).toHaveValue(-1);
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("o erro das horas aparece no campo das horas", async () => {
    const { user } = setup({
      mode: "POR_BLOCO_DE_HORAS",
      routes: { "PUT /api/activities/a1": { status: 422, body: { detail: [{ field: "horas", message: "Horas deve estar entre 0 e 10000" }] } } },
    });
    await submit(user);
    expect((await screen.findByText("Horas deve estar entre 0 e 10000")).id).toBe("horas-error");
  });
});

describe("SEC-12: erros 422 do editor de pontuação", () => {
  const issue = (field: string, message: string) => ({ "PUT /api/activities/a1": { status: 422, body: { detail: [{ field, message }] } } });

  it("o erro da quantidade recebe o foco no campo e é anunciado como alerta", async () => {
    const { user } = setup({ routes: issue("quantidade", "Quantidade deve ser um inteiro entre 0 e 10000") });
    await user.click(screen.getByRole("button", { name: "Salvar pontuação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Quantidade deve ser um inteiro entre 0 e 10000");
    expect(screen.getByLabelText("Quantidade")).toHaveFocus();
  });

  it("o erro do valor unitário recebe o foco no campo e é anunciado como alerta", async () => {
    const { user } = setup({ routes: issue("unit_points_override", "Valor unitário deve estar entre 0 e 10000") });
    await user.click(screen.getByRole("button", { name: "Salvar pontuação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Valor unitário deve estar entre 0 e 10000");
    expect(screen.getByLabelText("Valor unitário")).toHaveFocus();
  });

  it("o 422 de um campo que o editor não mostra aparece como alerta geral, sem falhar em silêncio", async () => {
    const { onSaved, user } = setup({ routes: issue("horas", "Horas só valem nos itens medidos por horas") });
    expect(screen.queryByLabelText("Horas")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salvar pontuação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Horas só valem nos itens medidos por horas");
    expect(onSaved).not.toHaveBeenCalled();
  });
});
