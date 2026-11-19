import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, ScoringGroup, Validity } from "../api/types";
import css from "../styles.css?raw";
import { mockFetch } from "../test/fetchMock";
import { ActivityRow } from "./ActivityRow";

const GROUPS: ScoringGroup[] = [
  {
    number: 3,
    name: "Bancas",
    counts_in_total: true,
    max_points: null,
    criteria: [
      { group_number: 3, item_number: 2, description: "Banca de mestrado", unit_label: "banca", mode: "POR_UNIDADE", unit_points: "4.00", hours_per_block: null, weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null, accepted_evidence: null, rules: null, review_note: null },
    ],
  },
];

const INTERSTICE = { interstice_start: "2024-01-01", interstice_end: "2025-12-31" };
const VALID: Validity = { state: "VALIDA", reason: null, needs_category: false, params: {} };

function activity(over: Partial<Activity> = {}): Activity {
  return {
    id: "a1",
    process_id: "p1",
    title: "Banca de mestrado de Maria",
    group_number: 3,
    item_number: 2,
    description: "",
    event_date: "2025-05-10",
    period_start: null,
    period_end: null,
    period_precision: "DAY",
    academic_period: null,
    level: null,
    quantidade: "1.00",
    horas: null,
    course_hours: null,
    informed_points: null,
    points_override: null,
    evidence_note: null,
    source: "SUGERIDA_IA",
    status: "AGUARDANDO_REVISAO",
    distinct_justification: null,
    candidates: [],
    evidences: [{ id: "e1", document_id: "d1", document_name: "ata-defesa.pdf", page: 2, excerpt: "" }],
    version: 4,
    validity: VALID,
    merged: [],
    predicted_points: "4.00",
    ...over,
  };
}

function setup(a: Activity, routes: Parameters<typeof mockFetch>[0] = {}, extra: { groups?: ScoringGroup[]; selectable?: boolean; selected?: boolean } = {}) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  const handlers = { onChanged: vi.fn(), onEdit: vi.fn(), onLink: vi.fn(), onToggleSelect: vi.fn() };
  render(
    <ul>
      <ActivityRow
        activity={a}
        groups={extra.groups ?? GROUPS}
        selected={extra.selected ?? false}
        onToggleSelect={extra.selectable === false ? undefined : handlers.onToggleSelect}
        onEdit={handlers.onEdit}
        onLink={handlers.onLink}
        onChanged={handlers.onChanged}
      />
    </ul>,
  );
  return { ...mock, ...handlers, user: userEvent.setup() };
}

const rowElement = () => document.querySelector("li.activity-row") as HTMLElement;
const body = (init: RequestInit | undefined) => JSON.parse(init?.body as string);

describe("VAL-06, SEC-04, SEC-12: ActivityRow", () => {
  it("atividade válida com categoria: título, data, categoria, pontos previstos, selo e Validar", () => {
    setup(activity());
    expect(screen.getByText("Banca de mestrado de Maria")).toBeInTheDocument();
    expect(screen.getByText("10/05/2025")).toBeInTheDocument();
    expect(screen.getByText("III.2 · Banca de mestrado")).toBeInTheDocument();
    expect(screen.getByText("Pontos previstos: 4,00")).toBeInTheDocument();
    expect(screen.getByText("Aguardando validação")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar Banca de mestrado de Maria" })).toBeInTheDocument();
    expect(screen.getByText("ata-defesa.pdf, página 2")).toBeInTheDocument();
  });

  it("atividade validada mostra o selo 'Validada' e não oferece Validar", () => {
    setup(activity({ status: "VALIDADA" }));
    expect(screen.getByText("Validada")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Validar / })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rejeitar Banca de mestrado de Maria" })).toBeInTheDocument();
  });

  it("sem categoria: selo 'Precisa de categoria', seletor na linha e nenhum Validar", () => {
    setup(
      activity({ group_number: null, item_number: null, predicted_points: null, validity: { ...VALID, needs_category: true } }),
    );
    expect(screen.getByText("Precisa de categoria")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Categoria de Banca de mestrado de Maria" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Validar / })).not.toBeInTheDocument();
  });

  it("escolher a categoria grava na hora, com o corpo completo, sem justificativa, e recarrega a lista", async () => {
    const saved = activity();
    const { calls, onChanged, user } = setup(
      activity({ group_number: null, item_number: null, predicted_points: null, validity: { ...VALID, needs_category: true } }),
      { "PUT /api/activities/a1": { status: 200, body: saved } },
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "Categoria de Banca de mestrado de Maria" }), "3.2");
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    const sent = body(calls[0].init);
    expect(sent).toMatchObject({
      title: "Banca de mestrado de Maria",
      event_date: "2025-05-10",
      group_number: 3,
      item_number: 2,
      expected_version: 4,
    });
    expect(sent).not.toHaveProperty("justificativa");
  });

  it("Validar chama o status VALIDADA com a versão, sem justificativa, e recarrega", async () => {
    const { calls, onChanged, user } = setup(activity(), {
      "POST /api/activities/a1/status": { status: 200, body: activity({ status: "VALIDADA" }) },
    });
    await user.click(screen.getByRole("button", { name: "Validar Banca de mestrado de Maria" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ status: "VALIDADA", expected_version: 4 });
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Rejeitar chama o status REJEITADA na hora", async () => {
    const { calls, onChanged, user } = setup(activity(), {
      "POST /api/activities/a1/status": { status: 200, body: activity({ status: "REJEITADA" }) },
    });
    await user.click(screen.getByRole("button", { name: "Rejeitar Banca de mestrado de Maria" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ status: "REJEITADA", expected_version: 4 });
  });

  it("422 de 'Escolha a categoria antes de validar' mostra a mensagem e recarrega a lista", async () => {
    const { onChanged, user } = setup(activity(), {
      "POST /api/activities/a1/status": {
        status: 422,
        body: { detail: [{ field: "categoria", code: "VALIDACAO", message: "Escolha a categoria antes de validar" }] },
      },
    });
    await user.click(screen.getByRole("button", { name: "Validar Banca de mestrado de Maria" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Escolha a categoria antes de validar");
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  it("atividade não válida: mostra o motivo em texto, sem Validar nem Rejeitar, com Editar", () => {
    setup(
      activity({
        predicted_points: null,
        validity: { state: "NAO_VALIDA", reason: "FORA_DO_INTERSTICIO", needs_category: false, params: { event_date: "2023-03-15", ...INTERSTICE } },
      }),
    );
    expect(screen.getByText("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Validar / })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Rejeitar / })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Editar Banca de mestrado de Maria" })).toBeInTheDocument();
    expect(screen.queryByText(/Pontos previstos/)).not.toBeInTheDocument();
  });

  it("atividade rejeitada mostra 'Rejeitada por você' e Reabrir, que volta a 'aguardando validação'", async () => {
    const { calls, onChanged, user } = setup(
      activity({ status: "REJEITADA", predicted_points: null, validity: { state: "NAO_VALIDA", reason: "REJEITADA", needs_category: false, params: {} } }),
      { "POST /api/activities/a1/status": { status: 200, body: activity() } },
    );
    expect(screen.getByText("Rejeitada por você")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Validar / })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reabrir Banca de mestrado de Maria" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ status: "AGUARDANDO_REVISAO", expected_version: 4 });
  });

  it("atividade sem vínculo mostra 'Sem documento vinculado'; a vinculada lista o documento e a página", () => {
    setup(activity({ evidences: [] }));
    expect(screen.getByText("Sem documento vinculado")).toBeInTheDocument();
    expect(screen.queryByText(/página/)).not.toBeInTheDocument();
  });

  it("REAL-09: atividade sem data mostra 'Sem data'; a datada mostra a data", () => {
    setup(activity({ event_date: null }));
    expect(screen.getByText("Sem data")).toBeInTheDocument();
    expect(screen.queryByText("10/05/2025")).not.toBeInTheDocument();
  });

  it("UIM-13: os rótulos visíveis são curtos e o título da atividade vai no nome acessível", () => {
    setup(activity());
    const buttons = within(rowElement()).getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Validar", "Rejeitar", "Editar", "Vincular"]);
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Validar Banca de mestrado de Maria",
      "Rejeitar Banca de mestrado de Maria",
      "Editar Banca de mestrado de Maria",
      "Vincular documento a Banca de mestrado de Maria",
    ]);
  });

  it("409 de versão desatualizada mostra o alerta e recarrega a lista", async () => {
    const { onChanged, user } = setup(activity(), {
      "POST /api/activities/a1/status": { status: 409, body: { detail: "A atividade foi alterada; recarregue" } },
    });
    await user.click(screen.getByRole("button", { name: "Validar Banca de mestrado de Maria" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A atividade foi alterada; recarregue");
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  it("Editar e Vincular avisam o pai com a atividade; a linha não abre painel sozinha", async () => {
    const { onEdit, onLink, user } = setup(activity());
    await user.click(screen.getByRole("button", { name: "Editar Banca de mestrado de Maria" }));
    await user.click(screen.getByRole("button", { name: "Vincular documento a Banca de mestrado de Maria" }));
    expect(onEdit).toHaveBeenCalledTimes(1);
    expect(onLink).toHaveBeenCalledTimes(1);
  });

  it("a atividade válida que aguarda validação pode ser selecionada; a seleção avisa o pai", async () => {
    const { onToggleSelect, user } = setup(activity());
    await user.click(screen.getByRole("checkbox", { name: "Selecionar Banca de mestrado de Maria" }));
    expect(onToggleSelect).toHaveBeenCalledTimes(1);
  });

  it("sem onToggleSelect, ou já validada, não há caixa de seleção", () => {
    setup(activity({ status: "VALIDADA" }));
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("mostra as duplicadas mescladas com 'Não é duplicada'", () => {
    setup(activity({ merged: [{ id: "m1", title: "Banca de mestrado de Maria (cópia)" }] }));
    expect(screen.getByText("1 duplicada mesclada")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Não é duplicada: Banca de mestrado de Maria (cópia)" })).toBeInTheDocument();
  });

  it("todo selo tem texto e todo botão tem nome acessível (não só cor)", () => {
    setup(activity({ merged: [{ id: "m1", title: "Cópia" }] }));
    const row = rowElement();
    for (const button of within(row).getAllByRole("button")) {
      expect(button).toHaveAccessibleName(/\S/);
    }
    expect(within(row).getByText("Aguardando validação")).toHaveClass("badge");
  });

  it("SEC-12: a linha é responsiva: quebra em linhas sem largura fixa", () => {
    setup(activity());
    expect(rowElement()).toHaveClass("activity-row");
    expect(css).toMatch(/\.activity-row\s*{[^}]*flex-wrap:\s*wrap/);
    const rule = css.match(/\.activity-row[^{]*{[^}]*}/g)?.join("\n") ?? "";
    expect(rule).not.toMatch(/(?:^|[\s;{])(?:width|min-width)\s*:\s*[1-9][\d.]*(?:px|rem|em)/);
  });
});
