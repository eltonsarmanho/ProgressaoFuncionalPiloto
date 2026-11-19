import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, DocumentSummary, ScoringGroup, Validity } from "../api/types";
import css from "../styles.css?raw";
import { mockFetch } from "../test/fetchMock";
import { ActivityWorkspace } from "./ActivityWorkspace";

const GROUPS: ScoringGroup[] = [
  {
    number: 3, name: "Bancas", counts_in_total: true, max_points: null,
    criteria: [
      { group_number: 3, item_number: 2, description: "Banca de mestrado", unit_label: "banca", mode: "POR_UNIDADE", unit_points: "4.00", hours_per_block: null, weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null, accepted_evidence: null, rules: null, review_note: null },
    ],
  },
];

const VALID: Validity = { state: "VALIDA", reason: null, needs_category: false, params: {} };
const OUT: Validity = {
  state: "NAO_VALIDA", reason: "FORA_DO_INTERSTICIO", needs_category: false,
  params: { event_date: "2023-03-15", interstice_start: "2024-01-01", interstice_end: "2025-12-31" },
};
const REJECTED: Validity = { state: "NAO_VALIDA", reason: "REJEITADA", needs_category: false, params: {} };

function activity(over: Partial<Activity> = {}): Activity {
  return {
    id: "a1", process_id: "p1", title: "Banca de mestrado de Maria", group_number: 3, item_number: 2, description: "",
    event_date: "2025-05-10", period_start: null, period_end: null, period_precision: "DAY", academic_period: null, level: null,
    quantidade: "1.00", horas: null, course_hours: null, informed_points: null, points_override: null, evidence_note: null,
    source: "SUGERIDA_IA", status: "AGUARDANDO_REVISAO", distinct_justification: null, candidates: [], evidences: [], version: 4,
    validity: VALID, merged: [], predicted_points: "4.00", ...over,
  };
}

const START = (): Activity[] => [
  activity({ id: "v1", title: "Banca válida" }),
  activity({ id: "o1", title: "Curso antigo", event_date: "2023-03-15", validity: OUT, predicted_points: null }),
  activity({ id: "r1", title: "Orientação rejeitada", status: "REJEITADA", validity: REJECTED, predicted_points: null }),
];

/** The parent of the workspace: `reload` gives the list the server would send after a write. */
function Harness({ initial, reload }: { initial: Activity[]; reload: (current: Activity[]) => Activity[] }) {
  const [list, setList] = useState(initial);
  return (
    <ActivityWorkspace
      processId="p1"
      activities={list}
      rows={[]}
      groups={GROUPS}
      documents={[] as DocumentSummary[]}
      onChanged={() => setList(reload)}
    />
  );
}

function setup(initial: Activity[], reload: (current: Activity[]) => Activity[] = (c) => c, routes: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  render(<Harness initial={initial} reload={reload} />);
  return { ...mock, user: userEvent.setup() };
}

const validRegion = () => screen.getByRole("region", { name: /^Atividades válidas/ });
const invalidRegion = () => screen.getByRole("region", { name: /^Atividades não válidas/ });
const openInvalid = (user: ReturnType<typeof userEvent.setup>) => user.click(screen.getByRole("button", { name: /^Atividades não válidas/ }));

describe("SEC-01: as duas seções", () => {
  it("separa as válidas das não válidas, cada uma com o total no título", () => {
    setup(START());
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (1)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: /^Atividades não válidas \(2\)/ })).toBeInTheDocument();
    expect(within(validRegion()).getByText("Banca válida")).toBeInTheDocument();
  });

  it("sem validade na resposta (resposta velha) a atividade é lida como válida", () => {
    setup([activity({ validity: null })]);
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (1)" })).toBeInTheDocument();
  });

  it("uma mesclada não aparece como linha: o título dela só está na nota da mantida", () => {
    setup([activity({ merged: [{ id: "m1", title: "Banca de mestrado de Maria (cópia)" }] })]);
    expect(document.querySelectorAll("li.activity-row")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Editar Banca de mestrado de Maria (cópia)" })).not.toBeInTheDocument();
    expect(screen.getByText("1 duplicada mesclada")).toBeInTheDocument();
  });
});

describe("SEC-08: corrigir uma não válida a leva às válidas, sem recarregar a página", () => {
  it("editar a data para dentro do interstício move a atividade para as válidas", async () => {
    const saved = activity({ id: "o1", title: "Curso antigo", event_date: "2025-03-15" });
    const { calls, user } = setup(
      START(),
      (current) => current.map((a) => (a.id === "o1" ? saved : a)),
      { "PUT /api/activities/o1": { status: 200, body: saved } },
    );
    await openInvalid(user);
    await user.click(screen.getByRole("button", { name: "Editar Curso antigo" }));
    const dialog = screen.getByRole("dialog", { name: "Editar atividade" });
    expect(within(dialog).queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    const date = within(dialog).getByLabelText(/^Data/);
    await user.clear(date);
    await user.type(date, "2025-03-15");
    await user.click(within(dialog).getByRole("button", { name: "Salvar atividade" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(JSON.parse(calls[0].init?.body as string)).toMatchObject({ event_date: "2025-03-15", expected_version: 4 });
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (2)" })).toBeInTheDocument();
    expect(within(validRegion()).getByText("Curso antigo")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: /^Atividades não válidas \(1\)/ })).toBeInTheDocument();
  });

  it("editar uma válida fecha a janela e a mantém nas válidas", async () => {
    const saved = activity({ id: "v1", title: "Banca corrigida" });
    const { user } = setup(
      START(),
      (current) => current.map((a) => (a.id === "v1" ? saved : a)),
      { "PUT /api/activities/v1": { status: 200, body: saved } },
    );
    await user.click(screen.getByRole("button", { name: "Editar Banca válida" }));
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(validRegion()).getByText("Banca corrigida")).toBeInTheDocument();
  });

  it("Cancelar fecha a janela sem salvar", async () => {
    const { calls, user } = setup(START());
    await user.click(screen.getByRole("button", { name: "Editar Banca válida" }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("reabrir uma rejeitada a move para as válidas", async () => {
    const reopened = activity({ id: "r1", title: "Orientação rejeitada" });
    const { user } = setup(
      START(),
      (current) => current.map((a) => (a.id === "r1" ? reopened : a)),
      { "POST /api/activities/r1/status": { status: 200, body: reopened } },
    );
    await openInvalid(user);
    await user.click(screen.getByRole("button", { name: "Reabrir Orientação rejeitada" }));
    await waitFor(() => expect(within(validRegion()).getByText("Orientação rejeitada")).toBeInTheDocument());
    expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (2)" })).toBeInTheDocument();
    const row = within(validRegion()).getByText("Orientação rejeitada").closest("li") as HTMLElement;
    expect(within(row).getByText("Aguardando validação")).toBeInTheDocument();
  });

  it("rejeitar uma válida a leva às não válidas", async () => {
    const rejected = activity({ id: "v1", title: "Banca válida", status: "REJEITADA", validity: REJECTED, predicted_points: null });
    const { user } = setup(
      START(),
      (current) => current.map((a) => (a.id === "v1" ? rejected : a)),
      { "POST /api/activities/v1/status": { status: 200, body: rejected } },
    );
    await user.click(screen.getByRole("button", { name: "Rejeitar Banca válida" }));
    await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (0)" })).toBeInTheDocument());
    expect(screen.getByRole("heading", { level: 2, name: /^Atividades não válidas \(3\)/ })).toBeInTheDocument();
  });
});

describe("SEC-12: teclado e largura de 360 px", () => {
  it("cada seção é uma região com o título como nome e o botão da não válida chega por Tab", async () => {
    const { user } = setup(START());
    expect(validRegion()).toBeInTheDocument();
    expect(invalidRegion()).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: /^Atividades não válidas/ });
    for (let i = 0; i < 40 && document.activeElement !== toggle; i += 1) await user.tab();
    expect(toggle).toHaveFocus();
  });

  it("nenhuma regra das seções e das linhas fixa largura nem força rolagem horizontal", () => {
    setup(START());
    const rules = css.match(/\.activity-(?:section|list|row|toolbar|filters)[^{]*{[^}]*}|\.section-toggle[^{]*{[^}]*}/g)?.join("\n") ?? "";
    expect(rules).not.toBe("");
    expect(rules).not.toMatch(/(?:^|[\s;{])(?:width|min-width)\s*:\s*[1-9][\d.]*(?:px|rem|em)/);
    expect(rules).not.toMatch(/overflow-x\s*:\s*scroll/);
  });
});

describe("notifica o pai", () => {
  it("depois de salvar a edição chama onChanged uma vez", async () => {
    setCsrfToken("tok");
    mockFetch({ "PUT /api/activities/v1": { status: 200, body: activity({ id: "v1" }) } });
    const onChanged = vi.fn();
    render(
      <ActivityWorkspace processId="p1" activities={START()} rows={[]} groups={GROUPS} documents={[]} onChanged={onChanged} />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Editar Banca válida" }));
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  });
});

describe("SEC-12: foco e anúncio depois de uma ação na linha", () => {
  const moveTo = (id: string, next: Activity) => (current: Activity[]) => current.map((a) => (a.id === id ? next : a));
  const status = () => screen.getByRole("status");

  it("Validar mantém o foco no título da linha e anuncia 'validada'", async () => {
    const validated = activity({ id: "v1", title: "Banca válida", status: "VALIDADA" });
    const { user } = setup(START(), moveTo("v1", validated), { "POST /api/activities/v1/status": { status: 200, body: validated } });
    await user.click(screen.getByRole("button", { name: "Validar Banca válida" }));
    await waitFor(() => expect(status()).toHaveTextContent("Banca válida validada"));
    expect(document.activeElement).toBe(within(validRegion()).getByText("Banca válida"));
  });

  it("Rejeitar, com outra linha na seção, leva o foco ao título da vizinha e anuncia 'rejeitada'", async () => {
    const rejected = activity({ id: "v1", title: "Banca um", status: "REJEITADA", validity: REJECTED, predicted_points: null });
    const { user } = setup([activity({ id: "v1", title: "Banca um" }), activity({ id: "v2", title: "Banca dois" })], moveTo("v1", rejected), {
      "POST /api/activities/v1/status": { status: 200, body: rejected },
    });
    await user.click(screen.getByRole("button", { name: "Rejeitar Banca um" }));
    await waitFor(() => expect(status()).toHaveTextContent("Banca um rejeitada"));
    await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (1)" })).toBeInTheDocument());
    expect(document.activeElement).toBe(within(validRegion()).getByText("Banca dois"));
  });

  it("Rejeitar a única linha da seção leva o foco ao título da seção, nunca ao body", async () => {
    const rejected = activity({ id: "v1", title: "Banca um", status: "REJEITADA", validity: REJECTED, predicted_points: null });
    const { user } = setup([activity({ id: "v1", title: "Banca um" })], moveTo("v1", rejected), {
      "POST /api/activities/v1/status": { status: 200, body: rejected },
    });
    await user.click(screen.getByRole("button", { name: "Rejeitar Banca um" }));
    await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: "Atividades válidas (0)" })).toBeInTheDocument());
    expect(document.activeElement).toBe(screen.getByRole("heading", { level: 2, name: "Atividades válidas (0)" }));
    expect(status()).toHaveTextContent("Banca um rejeitada");
  });

  it("Reabrir leva o foco ao título da linha na seção das válidas e anuncia 'reaberta'", async () => {
    const reopened = activity({ id: "r1", title: "Orientação rejeitada" });
    const { user } = setup(START(), moveTo("r1", reopened), { "POST /api/activities/r1/status": { status: 200, body: reopened } });
    await openInvalid(user);
    await user.click(screen.getByRole("button", { name: "Reabrir Orientação rejeitada" }));
    await waitFor(() => expect(status()).toHaveTextContent("Orientação rejeitada reaberta"));
    await waitFor(() => expect(within(validRegion()).getByText("Orientação rejeitada")).toBeInTheDocument());
    expect(document.activeElement).toBe(within(validRegion()).getByText("Orientação rejeitada"));
  });

  it("escolher a categoria na linha grava na hora, devolve o foco ao título e anuncia o resultado", async () => {
    const needs = activity({ id: "n1", title: "Sem categoria", group_number: null, item_number: null, predicted_points: null, validity: { ...VALID, needs_category: true } });
    const done = activity({ id: "n1", title: "Sem categoria" });
    const { calls, user } = setup([needs], moveTo("n1", done), { "PUT /api/activities/n1": { status: 200, body: done } });
    await user.selectOptions(screen.getByRole("combobox", { name: "Categoria de Sem categoria" }), "3.2");
    expect(calls).toHaveLength(1);
    await waitFor(() => expect(status()).toHaveTextContent("Categoria definida em Sem categoria"));
    await waitFor(() => expect(screen.queryByRole("combobox", { name: "Categoria de Sem categoria" })).not.toBeInTheDocument());
    expect(document.activeElement).toBe(within(validRegion()).getByText("Sem categoria"));
  });

  it("salvar a edição de uma não válida que passa às válidas leva o foco ao título dela e anuncia 'salva'", async () => {
    const saved = activity({ id: "o1", title: "Curso antigo", event_date: "2025-03-15" });
    const { user } = setup(START(), moveTo("o1", saved), { "PUT /api/activities/o1": { status: 200, body: saved } });
    await openInvalid(user);
    await user.click(screen.getByRole("button", { name: "Editar Curso antigo" }));
    const date = within(screen.getByRole("dialog")).getByLabelText(/^Data/);
    await user.clear(date);
    await user.type(date, "2025-03-15");
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(within(validRegion()).getByText("Curso antigo")).toBeInTheDocument());
    expect(document.activeElement).toBe(within(validRegion()).getByText("Curso antigo"));
    expect(status()).toHaveTextContent("Atividade Curso antigo salva");
  });

  it("a região de anúncio existe desde a abertura, vazia", () => {
    setup(START());
    expect(status()).toBeEmptyDOMElement();
  });
});
