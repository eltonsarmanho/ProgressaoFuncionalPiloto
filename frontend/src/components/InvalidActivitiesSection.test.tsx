import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity, InvalidReason, ScoringGroup, Validity } from "../api/types";
import css from "../styles.css?raw";
import { mockFetch } from "../test/fetchMock";
import { InvalidActivitiesSection } from "./InvalidActivitiesSection";

const GROUPS: ScoringGroup[] = [
  {
    number: 3, name: "Bancas", counts_in_total: true, max_points: null,
    criteria: [
      { group_number: 3, item_number: 2, description: "Banca de mestrado", unit_label: "banca", mode: "POR_UNIDADE", unit_points: "4.00", hours_per_block: null, weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null, accepted_evidence: null, rules: null, review_note: null },
    ],
  },
];

const INTERSTICE = { interstice_start: "2024-01-01", interstice_end: "2025-12-31" };
const OUT: Validity = { state: "NAO_VALIDA", reason: "FORA_DO_INTERSTICIO", needs_category: false, params: { event_date: "2023-03-15", ...INTERSTICE } };
const HOURS: Validity = { state: "NAO_VALIDA", reason: "CARGA_HORARIA_INSUFICIENTE", needs_category: false, params: { hours: "12", min_hours: "20" } };
const REJECTED: Validity = { state: "NAO_VALIDA", reason: "REJEITADA", needs_category: false, params: {} };

function activity(over: Partial<Activity> = {}): Activity {
  return {
    id: "a1", process_id: "p1", title: "Curso antigo", group_number: 3, item_number: 2, description: "", event_date: "2023-03-15",
    period_start: null, period_end: null, period_precision: "DAY", academic_period: null, level: null, quantidade: "1.00", horas: null,
    course_hours: null, informed_points: null, points_override: null, evidence_note: null, source: "SUGERIDA_IA",
    status: "AGUARDANDO_REVISAO", distinct_justification: null, candidates: [], evidences: [], version: 2,
    validity: OUT, merged: [], predicted_points: null, ...over,
  };
}

const mixed = () => [
  activity({ id: "o1", title: "Fora um" }),
  activity({ id: "o2", title: "Fora dois" }),
  activity({ id: "h1", title: "Poucas horas", validity: HOURS }),
  activity({ id: "r1", title: "Rejeitada um", status: "REJEITADA", validity: REJECTED }),
];

function setup(list: Activity[], routes: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  const onEdit = vi.fn();
  const onChanged = vi.fn();
  render(<InvalidActivitiesSection activities={list} groups={GROUPS} onEdit={onEdit} onChanged={onChanged} />);
  return { ...mock, onEdit, onChanged, user: userEvent.setup() };
}

const toggle = () => screen.getByRole("button", { name: /^Atividades não válidas/ });
const rowsShown = () => document.querySelectorAll("li.activity-row").length;

describe("SEC-10: seção fechada ao abrir", () => {
  it("abre fechada, sem linhas, e o botão do título alterna aria-expanded", async () => {
    const { user } = setup(mixed());
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(rowsShown()).toBe(0);
    await user.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    expect(rowsShown()).toBe(4);
    await user.click(toggle());
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(rowsShown()).toBe(0);
  });

  it("o botão é focável por teclado e abre com Enter e com espaço", async () => {
    const { user } = setup(mixed());
    await user.tab();
    expect(toggle()).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    await user.keyboard(" ");
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
  });

  it("o botão controla o painel das linhas", async () => {
    const { user } = setup(mixed());
    await user.click(toggle());
    const panel = document.getElementById(toggle().getAttribute("aria-controls")!);
    expect(panel).not.toBeNull();
    expect(within(panel!).getAllByRole("listitem").length).toBeGreaterThan(0);
  });
});

describe("SEC-10: título com total e contagem por motivo", () => {
  it("mostra o total e quantas há de cada motivo, em texto", () => {
    setup(mixed());
    const heading = screen.getByRole("heading", { level: 2 });
    expect(heading).toHaveTextContent("Atividades não válidas (4)");
    expect(heading).toHaveTextContent("Rejeitada por você: 1");
    expect(heading).toHaveTextContent("Fora do interstício: 2");
    expect(heading).toHaveTextContent("Carga horária insuficiente: 1");
    expect(heading).not.toHaveTextContent("Duplicidade");
  });
});

describe("SEC-06, SEC-07: linhas com o motivo em texto", () => {
  it("cada linha mostra o motivo e Editar; só a rejeitada tem Reabrir; nenhuma tem Validar ou Vincular", async () => {
    const { user } = setup(mixed());
    await user.click(toggle());
    expect(screen.getAllByText("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025")).toHaveLength(2);
    expect(screen.getByText("Carga horária insuficiente: 12 h; o item exige 20 h")).toBeInTheDocument();
    expect(screen.getByText("Rejeitada por você")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Editar / })).toHaveLength(4);
    expect(screen.getAllByRole("button", { name: /^Reabrir / })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /^Validar / })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Vincular / })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });
});

describe("SEC-09, SEC-12: Editar e Reabrir", () => {
  it("Editar avisa o pai com a atividade", async () => {
    const list = mixed();
    const { onEdit, user } = setup(list);
    await user.click(toggle());
    await user.click(screen.getByRole("button", { name: "Editar Poucas horas" }));
    expect(onEdit).toHaveBeenCalledWith(list[2]);
  });

  it("Reabrir leva a 'aguardando validação' na hora e pede ao pai que recarregue", async () => {
    const { calls, onChanged, user } = setup(mixed(), { "POST /api/activities/r1/status": { status: 200, body: activity({ id: "r1" }) } });
    await user.click(toggle());
    await user.click(screen.getByRole("button", { name: "Reabrir Rejeitada um" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(JSON.parse(calls[0].init?.body as string)).toEqual({ status: "AGUARDANDO_REVISAO", expected_version: 2 });
  });
});

describe("SEC-11: vazia e 25 por vez", () => {
  it("sem atividade mostra 'Nenhuma atividade não válida' e o total zero", () => {
    setup([]);
    expect(screen.getByRole("heading", { level: 2, name: "Atividades não válidas (0)" })).toBeInTheDocument();
    expect(screen.getByText("Nenhuma atividade não válida")).toBeInTheDocument();
  });

  it("mostra 25 por vez, com 'Mostrar mais'", async () => {
    const many = Array.from({ length: 60 }, (_, i) => activity({ id: `x${i}`, title: `Fora ${String(i).padStart(2, "0")}` }));
    const { user } = setup(many);
    await user.click(toggle());
    expect(rowsShown()).toBe(25);
    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(rowsShown()).toBe(50);
    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(rowsShown()).toBe(60);
    expect(screen.queryByRole("button", { name: "Mostrar mais" })).not.toBeInTheDocument();
  });

  it("SEC-12: o título não fixa largura", () => {
    setup(mixed());
    const rules = css.match(/\.section-toggle[^{]*{[^}]*}/g)?.join("\n") ?? "";
    expect(rules).not.toBe("");
    expect(rules).not.toMatch(/(?:^|[\s;{])(?:width|min-width)\s*:\s*[1-9][\d.]*(?:px|rem|em)/);
  });
});

describe("motivos", () => {
  it.each<[InvalidReason, string]>([
    ["GRUPO_NAO_CONTA", "Grupo não conta no total"],
    ["DUPLICIDADE", "Duplicidade"],
  ])("o motivo %s entra na contagem e na linha", async (reason, text) => {
    const { user } = setup([activity({ validity: { state: "NAO_VALIDA", reason, needs_category: false, params: {} } })]);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(`${text}: 1`);
    await user.click(toggle());
    expect(within(document.querySelector("li.activity-row") as HTMLElement).getByText(text)).toBeInTheDocument();
  });
});

describe("SEC-12: 'Mostrar mais' mantém o foco e o contador é anunciado", () => {
  it("o foco vai à primeira linha nova e o contador é uma região viva educada", async () => {
    const list = Array.from({ length: 60 }, (_, i) => activity({ id: `x${i + 1}`, title: `Fora ${String(i + 1).padStart(3, "0")}` }));
    const { user } = setup(list);
    await user.click(toggle());
    const counter = screen.getByText("Mostrando 25 de 60");
    expect(counter).toHaveAttribute("aria-live", "polite");
    await user.click(screen.getByRole("button", { name: "Mostrar mais" }));
    expect(screen.getByText("Mostrando 50 de 60")).toBe(counter);
    expect(document.activeElement).toBe(screen.getByText("Fora 026"));
  });
});
