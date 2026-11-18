import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Activity } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ProcessActivities } from "./ProcessActivities";

function activity(over: Partial<Activity> = {}): Activity {
  return {
    id: "a1", process_id: "p1", title: "Banca de mestrado", group_number: 3, item_number: 2, description: "", event_date: null,
    period_start: null, period_end: null, period_precision: "DAY", academic_period: null, level: null, quantidade: "1.00", horas: null,
    course_hours: null, informed_points: null, points_override: null, evidence_note: null, source: "SUGERIDA_IA",
    status: "AGUARDANDO_REVISAO", distinct_justification: null, candidates: [],
    evidences: [{ id: "e1", document_id: "d1", document_name: "ata.pdf", page: 2, excerpt: "" }], version: 2, ...over,
  };
}

const RESULT = {
  rows: [{ activity_id: "a1", title: "Banca de mestrado", activity_status: "AGUARDANDO_REVISAO", evidence_note: null, group_number: 3, item_number: 2, unit_points: "4.00", effective_quantity: "1.00", formula_text: null, points: "4.00", pit_hours: null, status: "POTENCIAL", reasons: [], alerts: [] }],
};

const ROUTES = {
  "GET /api/processes/p1/documents": { status: 200, body: [{ id: "d1", original_name: "ata.pdf" }] },
  "GET /api/processes/p1/scoring/table": { status: 200, body: { chosen: null, suggested: null, alerts: [] } },
  "GET /api/processes/p1/scoring": { status: 200, body: RESULT },
};
const LIST = "GET /api/processes/p1/activities";
const count = (calls: { method: string; path: string }[], key: string) => calls.filter((c) => `${c.method} ${c.path}` === key).length;

function renderPage(routes: Parameters<typeof mockFetch>[0]) {
  setCsrfToken("tok");
  const mock = mockFetch({ ...ROUTES, ...routes });
  render(
    <MemoryRouter initialEntries={["/processos/p1/atividades"]}>
      <Routes>
        <Route path="processos/:id/atividades" element={<ProcessActivities />} />
      </Routes>
    </MemoryRouter>,
  );
  return { ...mock, user: userEvent.setup() };
}

describe("TELA-06: página da Etapa 3", () => {
  it("carrega as atividades do processo com a navegação na Etapa 3 e o link para a Etapa 4", async () => {
    renderPage({ [LIST]: { status: 200, body: [activity()] } });
    const row = (await screen.findByText("Banca de mestrado", { selector: "td" })).closest("tr")!;
    expect(row).toHaveTextContent("ata.pdf, página 2");
    expect(row).toHaveTextContent("4,00 (Potencial)");
    expect(screen.getByRole("heading", { name: "Etapa 3 · Atividades" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getAllByRole("listitem")[2]).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("link", { name: "Ir para a Etapa 4 · Pontuação" })).toHaveAttribute("href", "/processos/p1/pontuacao");
  });

  it("sem o resultado da pontuação a lista continua funcionando, sem pontuação potencial", async () => {
    renderPage({ [LIST]: { status: 200, body: [activity()] }, "GET /api/processes/p1/scoring": { status: 500, body: { detail: "falha" } } });
    const row = (await screen.findByText("Banca de mestrado", { selector: "td" })).closest("tr")!;
    expect(within(row).getByText("—", { selector: "td[data-label='Pontuação potencial']" })).toBeInTheDocument();
  });

  it("erro ao carregar as atividades aparece como alerta", async () => {
    renderPage({ [LIST]: { status: 404, body: { detail: "Processo não encontrado" } } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Processo não encontrado");
  });

  it("validar recarrega a lista e mostra o novo status", async () => {
    let validated = false;
    const { calls, user } = renderPage({
      [LIST]: () => ({ status: 200, body: [activity({ status: validated ? "VALIDADA" : "AGUARDANDO_REVISAO" })] }),
      "POST /api/activities/a1/status": () => {
        validated = true;
        return { status: 200, body: activity({ status: "VALIDADA" }) };
      },
    });
    await user.click(await screen.findByRole("button", { name: "Validar Banca de mestrado" }));
    await waitFor(() => expect(screen.getByText("Validada")).toBeInTheDocument());
    expect(count(calls, LIST)).toBe(2);
  });

  it("rejeitar recarrega a lista", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [activity()] },
      "POST /api/activities/a1/status": { status: 200, body: activity({ status: "REJEITADA" }) },
    });
    await user.click(await screen.findByRole("button", { name: "Rejeitar Banca de mestrado" }));
    await waitFor(() => expect(count(calls, LIST)).toBe(2));
  });

  it("editar recarrega a lista depois de salvar, sem justificativa", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [activity()] },
      "PUT /api/activities/a1": { status: 200, body: activity({ title: "Banca corrigida" }) },
    });
    await user.click(await screen.findByRole("button", { name: "Editar Banca de mestrado" }));
    expect(screen.queryByLabelText("Justificativa da alteração")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Salvar atividade" }));
    await waitFor(() => expect(count(calls, LIST)).toBe(2));
  });

  it("validar as selecionadas chama a rota em lote só com os ids, sem justificativa, e recarrega", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [activity(), activity({ id: "a2", title: "Segunda banca" })] },
      "POST /api/processes/p1/activities/validate-batch": { status: 200, body: [] },
    });
    await user.click(await screen.findByLabelText("Selecionar Banca de mestrado"));
    await user.click(screen.getByLabelText("Selecionar Segunda banca"));
    await user.click(screen.getByRole("button", { name: "Validar as selecionadas (2)" }));

    await waitFor(() => expect(count(calls, LIST)).toBe(2));
    const batch = calls.find((c) => c.path === "/api/processes/p1/activities/validate-batch")!;
    expect(JSON.parse(batch.init?.body as string)).toEqual({ activity_ids: ["a1", "a2"] });
  });
});
