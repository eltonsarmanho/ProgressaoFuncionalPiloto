import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Criterion } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { CriterionEditDialog } from "./CriterionEditDialog";

const CRITERION: Criterion = {
  group_number: 2,
  item_number: 7,
  description: "Orientação de TCC",
  unit_label: "orientação",
  mode: "POR_UNIDADE",
  unit_points: "10.00",
  hours_per_block: null,
  weeks_per_semester: null,
  prep_ratio: null,
  min_hours: null,
  max_points: "30.00",
  accepted_evidence: "Declaração do orientador",
  rules: null,
  review_note: null,
};
const PATH = "PUT /api/scoring-versions/v1/criteria/2/7";

function setup(routes: Parameters<typeof mockFetch>[0] = {}, criterion: Criterion = CRITERION) {
  setCsrfToken("csrf-abc");
  const mock = mockFetch({ ...routes });
  const onSaved = vi.fn();
  const onClose = vi.fn();
  render(<CriterionEditDialog versionId="v1" criterion={criterion} onSaved={onSaved} onClose={onClose} />);
  return { ...mock, onSaved, onClose, user: userEvent.setup() };
}

function sent(calls: { method: string; path: string; init?: RequestInit }[]) {
  const call = calls.find((c) => `${c.method} ${c.path}` === PATH);
  return call ? JSON.parse(String(call.init?.body)) : undefined;
}

async function reference(user: ReturnType<typeof userEvent.setup>, text = "Res. sintética 3/2026, art. 2º") {
  await user.type(screen.getByLabelText("Referência normativa da alteração"), text);
}

const save = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: "Salvar critério" }));

describe("GTAB-18, GTAB-21: editar um critério", () => {
  it("o diálogo se chama pelo item e mostra os valores atuais, com o modo em português", () => {
    setup();

    const dialog = screen.getByRole("dialog", { name: "Editar critério II.7" });
    expect(within(dialog).getByLabelText("Descrição")).toHaveValue("Orientação de TCC");
    expect(within(dialog).getByLabelText("Pontos por unidade")).toHaveValue("10.00");
    expect(within(dialog).getByLabelText("Limite de pontos")).toHaveValue("30.00");
    const mode = within(dialog).getByLabelText("Modo de pontuação");
    expect(mode).toHaveValue("POR_UNIDADE");
    expect(within(mode).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Por unidade",
      "Por bloco de horas",
      "Carga semanal",
      "Valor informado",
    ]);
  });

  it("o PUT leva só os campos alterados, com decimais e inteiros nos tipos certos, e a referência", async () => {
    const { calls, onSaved, user } = setup({ [PATH]: { status: 200, body: { ...CRITERION, unit_points: "12.50" } } });

    const points = screen.getByLabelText("Pontos por unidade");
    await user.clear(points);
    await user.type(points, "12,5");
    const max = screen.getByLabelText("Limite de pontos");
    await user.clear(max);
    await user.type(max, "40");
    await user.type(screen.getByLabelText("Semanas por semestre"), "17");
    await user.type(screen.getByLabelText("Regras"), "Máximo de 2 por semestre");
    await reference(user);
    await save(user);

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(sent(calls)).toEqual({
      change_reference: "Res. sintética 3/2026, art. 2º",
      changes: { unit_points: 12.5, max_points: 40, weeks_per_semester: 17, rules: "Máximo de 2 por semestre" },
    });
    expect(onSaved).toHaveBeenCalledWith({ ...CRITERION, unit_points: "12.50" });
  });

  it("o modo escolhido pelo rótulo em português envia o valor do enum", async () => {
    const { calls, onSaved, user } = setup({ [PATH]: { status: 200, body: CRITERION } });

    await user.selectOptions(screen.getByLabelText("Modo de pontuação"), "Por bloco de horas");
    await reference(user);
    await save(user);

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(sent(calls).changes).toEqual({ mode: "POR_BLOCO_DE_HORAS" });
  });

  it("esvaziar um decimal envia null e o mesmo valor com outro formato não conta como alteração", async () => {
    const { calls, onSaved, user } = setup({ [PATH]: { status: 200, body: CRITERION } });

    await user.clear(screen.getByLabelText("Limite de pontos"));
    const points = screen.getByLabelText("Pontos por unidade");
    await user.clear(points);
    await user.type(points, "10");
    await reference(user);
    await save(user);

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled());
    expect(sent(calls).changes).toEqual({ max_points: null });
  });

  it("sem a referência normativa o envio é barrado e o campo mostra o erro", async () => {
    const { calls, onSaved, user } = setup();

    await user.clear(screen.getByLabelText("Pontos por unidade"));
    await user.type(screen.getByLabelText("Pontos por unidade"), "11");
    await save(user);

    const field = screen.getByLabelText("Referência normativa da alteração");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Informe a referência normativa da alteração.")).toBeInTheDocument();
    expect(calls).toEqual([]);
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("sem alteração o envio é barrado com 'Nenhuma alteração informada'", async () => {
    const { calls, user } = setup();

    await reference(user);
    await save(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("Nenhuma alteração informada");
    expect(calls).toEqual([]);
  });

  it("'Semanas por semestre' não aceita decimal, zero nem texto", async () => {
    const { calls, user } = setup();
    const weeks = screen.getByLabelText("Semanas por semestre");
    await reference(user);

    for (const bad of ["1,5", "0", "abc"]) {
      await user.clear(weeks);
      await user.type(weeks, bad);
      await save(user);
      expect(await screen.findByText("Informe um número inteiro positivo.")).toBeInTheDocument();
      expect(weeks).toHaveAttribute("aria-invalid", "true");
    }
    expect(calls).toEqual([]);
  });

  it("um decimal inválido ou negativo é barrado junto do campo", async () => {
    const { calls, user } = setup();
    const points = screen.getByLabelText("Pontos por unidade");
    await reference(user);

    for (const bad of ["abc", "-3"]) {
      await user.clear(points);
      await user.type(points, bad);
      await save(user);
      expect(await screen.findByText("Informe um número não negativo.")).toBeInTheDocument();
    }
    expect(calls).toEqual([]);
  });

  it("o 422 de um valor aparece junto do campo e mantém o que foi digitado", async () => {
    const { onSaved, user } = setup({
      [PATH]: { status: 422, body: { detail: [{ field: "max_points", message: "Valor deve ser um número não negativo" }] } },
    });

    const max = screen.getByLabelText("Limite de pontos");
    await user.clear(max);
    await user.type(max, "99");
    await user.type(screen.getByLabelText("Regras"), "texto novo");
    await reference(user);
    await save(user);

    expect(await screen.findByText("Valor deve ser um número não negativo")).toBeInTheDocument();
    expect(max).toHaveAttribute("aria-invalid", "true");
    expect(max).toHaveValue("99");
    expect(screen.getByLabelText("Regras")).toHaveValue("texto novo");
    expect(screen.getByLabelText("Referência normativa da alteração")).toHaveValue("Res. sintética 3/2026, art. 2º");
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("o 409 da API (versão passou a ser usada) aparece como texto no diálogo", async () => {
    const { onSaved, user } = setup({
      [PATH]: { status: 409, body: { detail: "A versão é usada por 2 processos", code: "VERSAO_USADA_POR_PROCESSO" } },
    });

    await user.type(screen.getByLabelText("Regras"), "x");
    await reference(user);
    await save(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("A versão é usada por 2 processos");
    expect(onSaved).not.toHaveBeenCalled();
  });
});
