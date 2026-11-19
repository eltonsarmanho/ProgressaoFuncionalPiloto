import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, DocumentSummary, ScoringGroup, ScoringRow, Validity } from "../api/types";
import css from "../styles.css?raw";
import { mockFetch } from "../test/fetchMock";
import { ValidActivitiesSection } from "./ValidActivitiesSection";

const criterion = (group: number, item: number, description: string) => ({
  group_number: group, item_number: item, description, unit_label: "unidade", mode: "POR_UNIDADE" as const, unit_points: "4.00",
  hours_per_block: null, weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null, accepted_evidence: null,
  rules: null, review_note: null,
});
const GROUPS: ScoringGroup[] = [
  { number: 2, name: "Orientação", counts_in_total: true, max_points: null, criteria: [criterion(2, 7, "Orientação de TCC")] },
  { number: 3, name: "Bancas", counts_in_total: true, max_points: null, criteria: [criterion(3, 2, "Banca de mestrado")] },
];

const VALID: Validity = { state: "VALIDA", reason: null, needs_category: false, params: {} };
const NEEDS: Validity = { ...VALID, needs_category: true };

function activity(over: Partial<Activity> = {}): Activity {
  return {
    id: "a1", process_id: "p1", title: "Banca de mestrado de Maria", group_number: 3, item_number: 2, description: "",
    event_date: "2025-05-10", period_start: null, period_end: null, period_precision: "DAY", academic_period: null, level: null,
    quantidade: "1.00", horas: null, course_hours: null, informed_points: null, points_override: null, evidence_note: null,
    source: "SUGERIDA_IA", status: "AGUARDANDO_REVISAO", distinct_justification: null, candidates: [],
    evidences: [{ id: "e1", document_id: "d1", document_name: "ata-defesa.pdf", page: 2, excerpt: "" }], version: 4,
    validity: VALID, merged: [], predicted_points: "4.00", ...over,
  };
}

/** n activities "Atividade 001..": the first `needs` need a category, the next `done` are validated. */
function many(n: number, { needs = 0, done = 0 }: { needs?: number; done?: number } = {}): Activity[] {
  return Array.from({ length: n }, (_, i) => {
    const id = `m${i + 1}`;
    const title = `Atividade ${String(i + 1).padStart(3, "0")}`;
    if (i < needs) return activity({ id, title, group_number: null, item_number: null, validity: NEEDS, predicted_points: null });
    if (i < needs + done) return activity({ id, title, status: "VALIDADA" });
    return activity({ id, title, group_number: i % 2 === 0 ? 3 : 2, item_number: i % 2 === 0 ? 2 : 7 });
  });
}

const ROW = (id: string, status: ScoringRow["status"] = "POTENCIAL"): ScoringRow => ({
  activity_id: id, title: "x", activity_status: "AGUARDANDO_REVISAO", evidence_note: null, group_number: 3, item_number: 2,
  unit_points: "4.00", effective_quantity: "1.00", formula_text: null, points: "4.00", pit_hours: null, status, reasons: [], alerts: [],
});

const DOCS = [{ id: "d1", original_name: "ata-defesa.pdf" }, { id: "d2", original_name: "portaria.pdf" }] as DocumentSummary[];

function setup(
  activities: Activity[],
  routes: Parameters<typeof mockFetch>[0] = {},
  extra: { documents?: DocumentSummary[]; rows?: ScoringRow[] } = {},
) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  const onChanged = vi.fn();
  const onEdit = vi.fn();
  render(
    <ValidActivitiesSection
      processId="p1"
      activities={activities}
      rows={extra.rows ?? activities.map((a) => ROW(a.id))}
      groups={GROUPS}
      documents={extra.documents ?? DOCS}
      onEdit={onEdit}
      onChanged={onChanged}
    />,
  );
  return { ...mock, onChanged, onEdit, user: userEvent.setup() };
}

const body = (init: RequestInit | undefined) => JSON.parse(init?.body as string);
const rowsShown = () => document.querySelectorAll("li.activity-row").length;
const BATCH = "POST /api/processes/p1/activities/validate-batch";

describe("SEC-02: lista de 25 em 25", () => {
  it("com 120 atividades mostra 25, o título traz o total e 'Mostrar mais' acrescenta 25", async () => {
    const { user } = setup(many(120));
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (120)" })).toBeInTheDocument();
    expect(rowsShown()).toBe(25);
    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(rowsShown()).toBe(50);
    expect(screen.getByText("Mostrando 50 de 120")).toBeInTheDocument();
  });

  it("até 25 atividades não oferece 'Mostrar mais'", () => {
    setup(many(25));
    expect(rowsShown()).toBe(25);
    expect(screen.queryByRole("button", { name: "Mostrar mais" })).not.toBeInTheDocument();
  });

  it("sem atividades mostra 'Nenhuma atividade válida ainda'", () => {
    setup([]);
    expect(screen.getByText("Nenhuma atividade válida ainda")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (0)" })).toBeInTheDocument();
  });
});

describe("SEC-03: busca e filtros sobre a lista inteira", () => {
  it("os chips contam sobre a lista inteira, e escolher um filtra e volta à primeira página", async () => {
    const { user } = setup(many(120, { needs: 10, done: 30 }));
    expect(screen.getByRole("button", { name: "Todas (120)" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Aguardando validação (80)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validadas (30)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Precisa de categoria (10)" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(rowsShown()).toBe(50);
    await user.click(screen.getByRole("button", { name: "Validadas (30)" }));
    expect(screen.getByRole("button", { name: "Validadas (30)" })).toHaveAttribute("aria-pressed", "true");
    expect(rowsShown()).toBe(25);
    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(rowsShown()).toBe(30);
    // The counts do not change with the filter.
    expect(screen.getByRole("button", { name: "Todas (120)" })).toBeInTheDocument();
  });

  it("a busca por título ignora maiúsculas e acentos; sem resultado avisa e Limpar filtros volta ao padrão", async () => {
    const list = [activity({ id: "a1", title: "Orientação de TCC" }), activity({ id: "a2", title: "Banca de mestrado" })];
    const { user } = setup(list);
    await user.type(screen.getByLabelText("Buscar por título"), "orientacao");
    expect(rowsShown()).toBe(1);
    expect(screen.getByText("Orientação de TCC")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Buscar por título"));
    await user.type(screen.getByLabelText("Buscar por título"), "zzz");
    expect(rowsShown()).toBe(0);
    expect(screen.getByText("Nenhuma atividade encontrada com estes filtros.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Limpar filtros" }));
    expect(rowsShown()).toBe(2);
  });

  it("o filtro por grupo lista só os grupos presentes e filtra", async () => {
    const list = [activity({ id: "a1", title: "Banca A" }), activity({ id: "a2", title: "Orientação B", group_number: 2, item_number: 7 })];
    const { user } = setup(list);
    const select = screen.getByLabelText("Filtrar por grupo");
    const options = within(select).getAllByRole("option").map((o) => o.textContent ?? "");
    expect(options).toHaveLength(3);
    expect(options[0]).toBe("Todos os grupos");
    expect(options[1]).toMatch(/^II · /);
    expect(options[2]).toMatch(/^III · /);
    await user.selectOptions(select, "2");
    expect(rowsShown()).toBe(1);
    expect(screen.getByText("Orientação B")).toBeInTheDocument();
  });
});

describe("SEC-05: aviso de categoria", () => {
  it("com atividade sem categoria mostra 'N atividades precisam de categoria'", () => {
    setup(many(5, { needs: 3 }));
    expect(screen.getByText("3 atividades precisam de categoria")).toBeInTheDocument();
  });

  it("sem atividade sem categoria não mostra o aviso", () => {
    setup(many(5));
    expect(screen.queryByText(/precisam? de categoria/)).not.toBeInTheDocument();
  });
});

describe("VAL-04: validar em lote", () => {
  it("mostra '12 validadas; 3 ficaram sem categoria' com a lista das que não foram validadas e recarrega", async () => {
    const list = many(4);
    const { calls, onChanged, user } = setup(list, {
      [BATCH]: {
        status: 200,
        body: {
          activities: [{ id: "m1" }, { id: "m2" }, { id: "m3" }],
          skipped: [{ id: "m4", reason: "SEM_CATEGORIA" }],
        },
      },
    });
    await user.click(screen.getByLabelText("Selecionar Atividade 001"));
    await user.click(screen.getByLabelText("Selecionar Atividade 004"));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ activity_ids: ["m1", "m4"] });
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent("3 validadas; 1 ficou sem categoria");
    expect(within(status).getByText("Atividade 004: sem categoria")).toBeInTheDocument();
  });

  it("com várias puladas usa o plural e conta as que não são válidas à parte", async () => {
    const list = many(5);
    const { user } = setup(list, {
      [BATCH]: {
        status: 200,
        body: {
          activities: Array.from({ length: 12 }, (_, i) => ({ id: `x${i}` })),
          skipped: [
            { id: "m1", reason: "SEM_CATEGORIA" },
            { id: "m2", reason: "SEM_CATEGORIA" },
            { id: "m3", reason: "SEM_CATEGORIA" },
            { id: "m4", reason: "FORA_DO_INTERSTICIO" },
          ],
        },
      },
    });
    await user.click(screen.getByRole("button", { name: "Selecionar todas (5)" }));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (5)" }));
    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent("12 validadas; 3 ficaram sem categoria; 1 não é válida");
    expect(within(status).getByText("Atividade 004: Fora do interstício")).toBeInTheDocument();
  });

  it("erro do servidor aparece como alerta e nada recarrega", async () => {
    const { onChanged, user } = setup(many(2), { [BATCH]: { status: 409, body: { detail: "A atividade foi alterada; recarregue" } } });
    await user.click(screen.getByLabelText("Selecionar Atividade 001"));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (1)" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A atividade foi alterada; recarregue");
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("REV-04 / UIM-11: seleção (portado de ActivityReviewList)", () => {
  it("o botão só habilita com seleção; a rota em lote recebe os ids, sem justificativa", async () => {
    const list = [activity(), activity({ id: "a2", title: "Segunda" }), activity({ id: "a3", title: "Terceira" })];
    const { calls, onChanged, user } = setup(list, { [BATCH]: { status: 200, body: { activities: [{}, {}], skipped: [] } } });
    expect(screen.getByRole("button", { name: "Validar as selecionadas (0)" })).toBeDisabled();
    await user.click(screen.getByLabelText("Selecionar Banca de mestrado de Maria"));
    await user.click(screen.getByLabelText("Selecionar Terceira"));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(body(calls[0].init)).toEqual({ activity_ids: ["a1", "a3"] });
    expect(screen.getByRole("status")).toHaveTextContent("2 validadas");
    expect(screen.getByLabelText("Selecionar Terceira")).not.toBeChecked();
  });

  const MIXED = () => [
    activity({ id: "a1", title: "Primeira" }),
    activity({ id: "a2", title: "Validada", status: "VALIDADA" }),
    activity({ id: "a4", title: "Quarta" }),
  ];

  it("Selecionar todas marca só as que aguardam validação e mostra a contagem", async () => {
    const { user } = setup(MIXED());
    await user.click(screen.getByRole("button", { name: "Selecionar todas (2)" }));
    expect(screen.getByLabelText("Selecionar Primeira")).toBeChecked();
    expect(screen.getByLabelText("Selecionar Quarta")).toBeChecked();
    expect(screen.queryByLabelText("Selecionar Validada")).not.toBeInTheDocument();
    expect(screen.getByText("2 atividades selecionadas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar as selecionadas (2)" })).toBeEnabled();
  });

  it("Limpar seleção zera tudo e Selecionar todas respeita o filtro", async () => {
    const { user } = setup(MIXED());
    await user.click(screen.getByRole("button", { name: "Selecionar todas (2)" }));
    await user.click(screen.getByRole("button", { name: "Limpar seleção" }));
    expect(screen.getByLabelText("Selecionar Quarta")).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Validar as selecionadas (0)" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Limpar seleção" })).toBeDisabled();

    await user.type(screen.getByLabelText("Buscar por título"), "quarta");
    expect(screen.getByRole("button", { name: "Selecionar todas (1)" })).toBeInTheDocument();
  });

  it("Validar as selecionadas depois de Selecionar todas envia só os ids que aguardam validação e têm categoria", async () => {
    const list = [...MIXED(), activity({ id: "a5", title: "Sem categoria", group_number: null, item_number: null, validity: NEEDS })];
    const { calls, onChanged, user } = setup(list, { [BATCH]: { status: 200, body: { activities: [{}, {}], skipped: [] } } });
    await user.click(screen.getByRole("button", { name: "Selecionar todas (2)" }));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ activity_ids: ["a1", "a4"] });
  });

  it("sem atividade aguardando validação, Selecionar todas fica desabilitado", () => {
    setup([activity({ status: "VALIDADA" })]);
    expect(screen.getByRole("button", { name: "Selecionar todas (0)" })).toBeDisabled();
  });
});

describe("VAL-04 / UIM-12: validar as confiáveis (portado de ActivityReviewList)", () => {
  const docs = (...items: [string, string, DocumentSummary["status"]?][]) =>
    items.map(([id, confidence, status]) => ({ id, original_name: `${id}.pdf`, confidence, status: status ?? "PROCESSADO" })) as DocumentSummary[];
  const linked = (id: string, title: string, doc: string, over: Partial<Activity> = {}) =>
    activity({ id, title, evidences: [{ id: `e-${id}`, document_id: doc, document_name: `${doc}.pdf`, page: 1, excerpt: "" }], ...over });
  const BUTTON = /^Validar as confiáveis/;

  function setupBulk(list: Activity[], documents: DocumentSummary[], rowOver: Record<string, Partial<ScoringRow>> = {}) {
    return setup(list, { [BATCH]: { status: 200, body: { activities: [{}, {}], skipped: [] } } }, {
      documents,
      rows: list.map((a) => ({ ...ROW(a.id), ...rowOver[a.id] })),
    });
  }

  it("valida numa só chamada as de 0,91 e 0,70, deixa a de 0,69 e informa quantas foram validadas", async () => {
    const list = [linked("a1", "Alta", "d1"), linked("a2", "Limite", "d2"), linked("a3", "Baixa", "d3")];
    const { calls, onChanged, user } = setupBulk(list, docs(["d1", "0.91"], ["d2", "0.70"], ["d3", "0.69"]));
    await user.click(screen.getByRole("button", { name: "Validar as confiáveis (2)" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls).toHaveLength(1);
    expect(body(calls[0].init)).toEqual({ activity_ids: ["a1", "a2"] });
    expect(screen.getByRole("status")).toHaveTextContent("2 validadas");
    expect(screen.getByRole("status")).toHaveTextContent("As demais continuam aguardando a sua revisão");
  });

  it("manual, com candidatos, sem documento, de documento falho, com alerta ou sem categoria não entram", async () => {
    const list = [
      linked("ok", "Entra", "d1"),
      linked("man", "Manual", "d1", { source: "MANUAL" }),
      linked("cand", "Candidatos", "d1", { candidates: [{ group_number: 4, item_number: 1, justification: "" }] }),
      activity({ id: "sem", title: "Sem documento", evidences: [] }),
      linked("fal", "Doc falho", "d4"),
      linked("alt", "Com alerta", "d1"),
      linked("val", "Já validada", "d1", { status: "VALIDADA" }),
      linked("cat", "Sem categoria", "d1", { group_number: null, item_number: null, validity: NEEDS }),
    ];
    const alert = { code: "INTERSTICIO_PARCIAL", severity: "ALERTA" as const, message: "parcial", norm_reference: "" };
    const { calls, user } = setupBulk(list, docs(["d1", "0.95"], ["d4", "0.95", "FALHOU"]), { alt: { alerts: [alert] } });
    await user.click(screen.getByRole("button", { name: BUTTON }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(body(calls[0].init)).toEqual({ activity_ids: ["ok"] });
  });

  it("documento revisado, sem IA ou sem confiança não entra e o botão fica desabilitado", () => {
    const list = [linked("rev", "Doc em revisão", "d2"), linked("ia", "Doc sem IA", "d3"), linked("nul", "Doc sem confiança", "d4")];
    setupBulk(list, docs(["d2", "0.95", "REQUER_REVISAO"], ["d3", "0.95", "EXTRAIDO_SEM_IA"]).concat([
      { id: "d4", original_name: "d4.pdf", confidence: null, status: "PROCESSADO" } as DocumentSummary,
    ]));
    expect(screen.getByRole("button", { name: BUTTON })).toBeDisabled();
    expect(screen.getByText("0 atividades elegíveis para a validação por confiança.")).toBeInTheDocument();
  });

  it("com vários documentos vale o de menor confiança", () => {
    const two = [
      linked("a1", "Duas fontes", "d1", {
        evidences: [
          { id: "e1", document_id: "d1", document_name: "d1.pdf", page: 1, excerpt: "" },
          { id: "e2", document_id: "d2", document_name: "d2.pdf", page: 1, excerpt: "" },
        ],
      }),
    ];
    setupBulk(two, docs(["d1", "0.95"], ["d2", "0.60"]));
    expect(screen.getByRole("button", { name: BUTTON })).toBeDisabled();
  });
});

describe("VINC / UIM-16 / FORA-03: vincular documento (portado de ActivityReviewList)", () => {
  it("envia o documento e a página, sem justificativa, fecha a janela e recarrega", async () => {
    const { calls, onChanged, user } = setup([activity()], { "POST /api/activities/a1/evidences": { status: 201, body: { id: "e9" } } });
    await user.click(screen.getByRole("button", { name: "Vincular documento a Banca de mestrado de Maria" }));
    const dialog = screen.getByRole("dialog", { name: "Vincular documento" });
    expect(within(dialog).queryByLabelText(/Justificativa/)).not.toBeInTheDocument();
    await user.selectOptions(within(dialog).getByLabelText("Documento"), "d2");
    await user.clear(within(dialog).getByLabelText("Página do documento"));
    await user.type(within(dialog).getByLabelText("Página do documento"), "3");
    await user.click(within(dialog).getByRole("button", { name: "Vincular" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ document_id: "d2", page: 3 });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("o seletor não oferece o documento fora do interstício", async () => {
    const docs = [...DOCS, { id: "d3", original_name: "antigo-2022.pdf", outside_interstice: true }] as DocumentSummary[];
    const { user } = setup([activity()], {}, { documents: docs });
    await user.click(screen.getByRole("button", { name: "Vincular documento a Banca de mestrado de Maria" }));
    const options = within(within(screen.getByRole("dialog")).getByLabelText("Documento")).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["Selecione…", "ata-defesa.pdf", "portaria.pdf"]);
  });

  it("o erro do servidor aparece na janela, que continua aberta", async () => {
    const { onChanged, user } = setup([activity()], {
      "POST /api/activities/a1/evidences": { status: 409, body: { detail: "Esta página já está ligada a esta atividade" } },
    });
    await user.click(screen.getByRole("button", { name: "Vincular documento a Banca de mestrado de Maria" }));
    await user.selectOptions(screen.getByLabelText("Documento"), "d1");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Vincular" }));
    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("Esta página já está ligada a esta atividade");
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("Editar e SEC-12", () => {
  it("Editar avisa o pai com a atividade", async () => {
    const a = activity();
    const { onEdit, user } = setup([a]);
    await user.click(screen.getByRole("button", { name: "Editar Banca de mestrado de Maria" }));
    expect(onEdit).toHaveBeenCalledWith(a);
  });

  it("a seção quebra em linhas e não fixa largura", () => {
    setup([activity()]);
    const rules = css.match(/\.activity-(?:section|toolbar)[^{]*{[^}]*}/g)?.join("\n") ?? "";
    expect(rules).not.toMatch(/(?:^|[\s;{])(?:width|min-width)\s*:\s*[1-9][\d.]*(?:px|rem|em)/);
    expect(css).toMatch(/\.activity-toolbar\s*{[^}]*flex-wrap:\s*wrap/);
  });
});

describe("SEC-12: 'Mostrar mais' mantém o foco e o contador é anunciado", () => {
  it("o foco vai à primeira linha nova e o contador é uma região viva educada", async () => {
    const { user } = setup(many(60, { }));
    const counter = screen.getByText("Mostrando 25 de 60");
    expect(counter).toHaveAttribute("aria-live", "polite");
    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(screen.getByText("Mostrando 50 de 60")).toBe(counter);
    expect(document.activeElement).toBe(screen.getByText("Atividade 026"));
  });
});
