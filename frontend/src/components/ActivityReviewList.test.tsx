import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, DocumentSummary, ScoringGroup, ScoringRow } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ActivityReviewList } from "./ActivityReviewList";

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
    ...over,
  };
}

const ROW = (id: string, points: string, status: ScoringRow["status"] = "POTENCIAL"): ScoringRow => ({
  activity_id: id, title: "x", activity_status: "AGUARDANDO_REVISAO", evidence_note: null, group_number: 3, item_number: 2,
  unit_points: "4.00", effective_quantity: "1.00", formula_text: null, points, pit_hours: null, status, reasons: [], alerts: [],
});

const DOCS = [{ id: "d1", original_name: "ata-defesa.pdf" }, { id: "d2", original_name: "portaria.pdf" }] as DocumentSummary[];

function setup(activities: Activity[], routes: Parameters<typeof mockFetch>[0] = {}, documents: DocumentSummary[] = DOCS) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  const onChanged = vi.fn();
  render(
    <ActivityReviewList
      processId="p1"
      activities={activities}
      rows={activities.map((a) => ROW(a.id, "4.00"))}
      groups={GROUPS}
      documents={documents}
      onChanged={onChanged}
    />,
  );
  return { ...mock, onChanged, user: userEvent.setup() };
}

const body = (init: RequestInit | undefined) => JSON.parse(init?.body as string);

describe("TELA-06: lista de revisão", () => {
  it("mostra origem, status, grupo e item, pontuação potencial e os documentos com a página", () => {
    setup([activity()]);
    const row = screen.getByText("Banca de mestrado de Maria", { selector: "td" }).closest("tr")!;
    expect(within(row).getByText("Sugerido pela IA")).toBeInTheDocument();
    expect(within(row).getByText("Aguardando revisão")).toBeInTheDocument();
    expect(row).toHaveTextContent("III.2");
    expect(row).toHaveTextContent("Banca de mestrado");
    expect(row).toHaveTextContent("4,00 (Potencial)");
    expect(row).toHaveTextContent("ata-defesa.pdf, página 2");
  });

  it("atividade sem vínculo mostra 'Sem documento vinculado' e a de horas de PIT mostra horas, não pontos", () => {
    setCsrfToken("tok");
    render(
      <ActivityReviewList
        processId="p1"
        activities={[activity({ id: "a2", evidences: [], group_number: 1, item_number: null })]}
        rows={[{ ...ROW("a2", "0.00"), group_number: 1, pit_hours: "8.00" }]}
        groups={GROUPS}
        documents={DOCS}
        onChanged={vi.fn()}
      />,
    );
    expect(screen.getByText("Sem documento vinculado")).toBeInTheDocument();
    expect(screen.getByText("8,00 horas (PIT) (Potencial)")).toBeInTheDocument();
  });

  it("REAL-09: atividade sem data é marcada 'sem data' ao lado do potencial; a datada não", () => {
    setCsrfToken("tok");
    const undated = {
      ...ROW("a2", "4.00"),
      alerts: [{ code: "DATA_AUSENTE", severity: "ALERTA" as const, message: "sem data", norm_reference: "" }],
    };
    render(
      <ActivityReviewList
        processId="p1"
        activities={[activity({ id: "a1" }), activity({ id: "a2", title: "Sem data alguma", event_date: null })]}
        rows={[ROW("a1", "4.00"), undated]}
        groups={GROUPS}
        documents={DOCS}
        onChanged={vi.fn()}
      />,
    );
    const dated = screen.getByText("Banca de mestrado de Maria", { selector: "td" }).closest("tr")!;
    const missing = screen.getByText("Sem data alguma", { selector: "td" }).closest("tr")!;
    expect(missing).toHaveTextContent("4,00 (Potencial) · sem data");
    expect(dated).not.toHaveTextContent("sem data");
  });

  it("em 360 px usa as células rotuladas dos cartões", () => {
    setup([activity()]);
    expect(screen.getByRole("table")).toHaveClass("scoring-table");
    const row = screen.getByText("Banca de mestrado de Maria", { selector: "td" }).closest("tr")!;
    expect(within(row).getAllByRole("cell").map((c) => c.getAttribute("data-label"))).toEqual([
      "Selecionar", "Atividade", "Origem", "Status", "Grupo e item", "Pontuação potencial", "Documentos", "Ações",
    ]);
  });
});

describe("UIM-10: colunas e texto justificado", () => {
  it("a tabela leva as classes das regras de coluna e o título e o item levam o texto justificado", () => {
    setup([activity()]);
    expect(screen.getByRole("table")).toHaveClass("wide-table", "review-table");
    const row = screen.getByText("Banca de mestrado de Maria", { selector: "td" }).closest("tr")!;
    expect(within(row).getByText("Banca de mestrado de Maria", { selector: "td" })).toHaveClass("text-block");
    expect(row.querySelector("td[data-label='Grupo e item']")).toHaveClass("text-block");
  });
});

describe("UIM-13: botões curtos de ação", () => {
  it("os rótulos visíveis são curtos e o título da atividade só vai no aria-label e no title", () => {
    setup([activity()]);
    const row = screen.getByText("Banca de mestrado de Maria", { selector: "td" }).closest("tr")!;
    const buttons = within(row).getAllByRole("button");

    expect(buttons.map((b) => b.textContent)).toEqual(["Validar", "Rejeitar", "Editar", "Vincular"]);
    expect(buttons.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Validar Banca de mestrado de Maria",
      "Rejeitar Banca de mestrado de Maria",
      "Editar Banca de mestrado de Maria",
      "Vincular documento a Banca de mestrado de Maria",
    ]);
    expect(buttons.map((b) => b.getAttribute("title"))).toEqual(buttons.map((b) => b.getAttribute("aria-label")));
  });
});

describe("REV-03 / UIM-13: validar e rejeitar na hora", () => {
  it("validar envia VALIDADA com a versão esperada, sem justificativa e sem painel, e recarrega", async () => {
    const { calls, onChanged, user } = setup([activity()], { "POST /api/activities/a1/status": { status: 200, body: activity({ status: "VALIDADA" }) } });
    await user.click(screen.getByRole("button", { name: "Validar Banca de mestrado de Maria" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ status: "VALIDADA", expected_version: 4 });
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("rejeitar envia REJEITADA na hora; atividade já validada não oferece validar de novo", async () => {
    const { calls, onChanged, user } = setup([activity(), activity({ id: "a2", title: "Outra", status: "VALIDADA" })], {
      "POST /api/activities/a1/status": { status: 200, body: activity({ status: "REJEITADA" }) },
    });
    expect(screen.getByRole("button", { name: "Validar Outra" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Rejeitar Banca de mestrado de Maria" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ status: "REJEITADA", expected_version: 4 });
  });

  it("erro 409 de versão desatualizada aparece como alerta e não recarrega", async () => {
    const { onChanged, user } = setup([activity()], { "POST /api/activities/a1/status": { status: 409, body: { detail: "A atividade foi alterada; recarregue" } } });
    await user.click(screen.getByRole("button", { name: "Validar Banca de mestrado de Maria" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A atividade foi alterada; recarregue");
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("REV-02: editar sem justificativa (UIM-17)", () => {
  it("abre o formulário de edição, sem campo de justificativa, e recarrega após salvar", async () => {
    const { calls, onChanged, user } = setup([activity()], { "PUT /api/activities/a1": { status: 200, body: activity({ title: "Banca corrigida" }) } });
    await user.click(screen.getByRole("button", { name: "Editar Banca de mestrado de Maria" }));
    expect(screen.getByRole("dialog", { name: "Editar atividade" })).toBeInTheDocument();
    const title = screen.getByLabelText("Título");
    await user.clear(title);
    await user.type(title, "Banca corrigida");
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toMatchObject({ title: "Banca corrigida", expected_version: 4 });
    expect(body(calls[0].init)).not.toHaveProperty("justificativa");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("VINC / UIM-16: vincular documento numa janela, sem justificativa", () => {
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

  it("FORA-03: o seletor não oferece o documento fora do interstício", async () => {
    const docs = [...DOCS, { id: "d3", original_name: "antigo-2022.pdf", outside_interstice: true }] as DocumentSummary[];
    const { user } = setup([activity()], {}, docs);
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

describe("REV-04 / UIM-11: validar as selecionadas", () => {
  it("o botão só habilita com seleção; a rota em lote recebe os ids, sem justificativa, e a contagem é informada", async () => {
    const { calls, onChanged, user } = setup([activity(), activity({ id: "a2", title: "Segunda" }), activity({ id: "a3", title: "Terceira" })], {
      "POST /api/processes/p1/activities/validate-batch": { status: 200, body: [{}, {}] },
    });
    expect(screen.getByRole("button", { name: "Validar as selecionadas (0)" })).toBeDisabled();
    await user.click(screen.getByLabelText("Selecionar Banca de mestrado de Maria"));
    await user.click(screen.getByLabelText("Selecionar Terceira"));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(body(calls[0].init)).toEqual({ activity_ids: ["a1", "a3"] });
    expect(screen.getByRole("status")).toHaveTextContent("2 atividades validadas");
  });
});

describe("UIM-11: selecionar todas", () => {
  const MIXED = () => [
    activity({ id: "a1", title: "Primeira" }),
    activity({ id: "a2", title: "Validada", status: "VALIDADA" }),
    activity({ id: "a3", title: "Rejeitada", status: "REJEITADA" }),
    activity({ id: "a4", title: "Quarta" }),
  ];

  it("Selecionar todas marca só as atividades aguardando revisão e mostra a contagem", async () => {
    const { user } = setup(MIXED());
    await user.click(screen.getByRole("button", { name: "Selecionar todas (2)" }));

    expect(screen.getByLabelText("Selecionar Primeira")).toBeChecked();
    expect(screen.getByLabelText("Selecionar Quarta")).toBeChecked();
    expect(screen.getByLabelText("Selecionar Validada")).not.toBeChecked();
    expect(screen.getByLabelText("Selecionar Rejeitada")).not.toBeChecked();
    expect(screen.getByText("2 atividades selecionadas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar as selecionadas (2)" })).toBeEnabled();
  });

  it("a caixa do cabeçalho alterna entre selecionar todas e limpar, e Limpar seleção zera tudo", async () => {
    const { user } = setup(MIXED());
    const header = screen.getByRole("checkbox", { name: "Selecionar todas as atividades que aguardam revisão" });

    await user.click(header);
    expect(header).toBeChecked();
    expect(screen.getByLabelText("Selecionar Primeira")).toBeChecked();

    await user.click(header);
    expect(header).not.toBeChecked();
    expect(screen.getByLabelText("Selecionar Primeira")).not.toBeChecked();

    await user.click(screen.getByRole("button", { name: "Selecionar todas (2)" }));
    await user.click(screen.getByRole("button", { name: "Limpar seleção" }));
    expect(screen.getByLabelText("Selecionar Quarta")).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Validar as selecionadas (0)" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Limpar seleção" })).toBeDisabled();
  });

  it("Validar as selecionadas depois de Selecionar todas envia só os ids que aguardam revisão", async () => {
    const { calls, onChanged, user } = setup(MIXED(), {
      "POST /api/processes/p1/activities/validate-batch": { status: 200, body: [{}, {}] },
    });
    await user.click(screen.getByRole("button", { name: "Selecionar todas (2)" }));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(body(calls[0].init)).toEqual({ activity_ids: ["a1", "a4"] });
  });

  it("sem atividade aguardando revisão, Selecionar todas fica desabilitado", () => {
    setup([activity({ status: "VALIDADA" })]);
    expect(screen.getByRole("button", { name: "Selecionar todas (0)" })).toBeDisabled();
  });
});

describe("UIM-12: validar todas com confiança a partir de 70%", () => {
  const docs = (...items: [string, string, DocumentSummary["status"]?][]) =>
    items.map(([id, confidence, status]) => ({ id, original_name: `${id}.pdf`, confidence, status: status ?? "PROCESSADO" })) as DocumentSummary[];
  const linked = (id: string, title: string, doc: string, over: Partial<Activity> = {}) =>
    activity({ id, title, evidences: [{ id: `e-${id}`, document_id: doc, document_name: `${doc}.pdf`, page: 1, excerpt: "" }], ...over });

  function setupBulk(activities: Activity[], documents: DocumentSummary[], rowOver: Record<string, Partial<ScoringRow>> = {}) {
    setCsrfToken("tok");
    const mock = mockFetch({ "POST /api/processes/p1/activities/validate-batch": { status: 200, body: [{}, {}] } });
    const onChanged = vi.fn();
    render(
      <ActivityReviewList
        processId="p1"
        activities={activities}
        rows={activities.map((a) => ({ ...ROW(a.id, "4.00"), ...rowOver[a.id] }))}
        groups={GROUPS}
        documents={documents}
        onChanged={onChanged}
      />,
    );
    return { ...mock, onChanged, user: userEvent.setup() };
  }
  const BUTTON = "Validar todas com confiança a partir de 70%";

  it("valida numa só chamada as de 0,91 e 0,70, deixa a de 0,69 e informa quantas foram validadas", async () => {
    const activities = [linked("a1", "Alta", "d1"), linked("a2", "Limite", "d2"), linked("a3", "Baixa", "d3")];
    const { calls, onChanged, user } = setupBulk(activities, docs(["d1", "0.91"], ["d2", "0.70"], ["d3", "0.69"]));

    await user.click(screen.getByRole("button", { name: BUTTON }));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls).toHaveLength(1);
    expect(body(calls[0].init)).toEqual({ activity_ids: ["a1", "a2"] });
    expect(screen.getByRole("status")).toHaveTextContent("2 atividades validadas");
    expect(screen.getByRole("status")).toHaveTextContent("As demais continuam aguardando a sua revisão");
  });

  it("manual, com candidatos, sem documento, de documento falho ou com alerta na linha não entram", async () => {
    const activities = [
      linked("ok", "Entra", "d1"),
      linked("man", "Manual", "d1", { source: "MANUAL" }),
      linked("cand", "Candidatos", "d1", { candidates: [{ group_number: 4, item_number: 1, justification: "" }] }),
      activity({ id: "sem", title: "Sem documento", evidences: [] }),
      linked("fal", "Doc falho", "d4"),
      linked("alt", "Com alerta", "d1"),
      linked("val", "Já validada", "d1", { status: "VALIDADA" }),
    ];
    const alert = { code: "INTERSTICIO_PARCIAL", severity: "ALERTA" as const, message: "parcial", norm_reference: "" };
    const { calls, user } = setupBulk(activities, docs(["d1", "0.95"], ["d4", "0.95", "FALHOU"]), { alt: { alerts: [alert] } });

    await user.click(screen.getByRole("button", { name: BUTTON }));

    await waitFor(() => expect(calls).toHaveLength(1));
    expect(body(calls[0].init)).toEqual({ activity_ids: ["ok"] });
  });

  it("sem item (grupo vazio) ou com documento revisado, sem IA ou sem confiança não entram", () => {
    const activities = [
      linked("sem-grupo", "Sem grupo", "d1", { group_number: null, item_number: null }),
      linked("rev", "Doc em revisão", "d2"),
      linked("ia", "Doc sem IA", "d3"),
      linked("nul", "Doc sem confiança", "d4"),
    ];
    setupBulk(activities, docs(["d1", "0.95"], ["d2", "0.95", "REQUER_REVISAO"], ["d3", "0.95", "EXTRAIDO_SEM_IA"]).concat([
      { id: "d4", original_name: "d4.pdf", confidence: null, status: "PROCESSADO" } as DocumentSummary,
    ]));
    expect(screen.getByRole("button", { name: BUTTON })).toBeDisabled();
    expect(screen.getByText("0 atividades elegíveis para a validação por confiança.")).toBeInTheDocument();
  });

  it("com vários documentos, vale o de menor confiança; sem atividade elegível o botão fica desabilitado", () => {
    const two = [linked("a1", "Duas fontes", "d1", { evidences: [
      { id: "e1", document_id: "d1", document_name: "d1.pdf", page: 1, excerpt: "" },
      { id: "e2", document_id: "d2", document_name: "d2.pdf", page: 1, excerpt: "" },
    ] })];
    setupBulk(two, docs(["d1", "0.95"], ["d2", "0.60"]));
    expect(screen.getByRole("button", { name: BUTTON })).toBeDisabled();
  });
});
