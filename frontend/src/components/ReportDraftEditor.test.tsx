import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { setCsrfToken } from "../api/client";
import type { ReportDraftView } from "../api/generated";
import { mockFetch } from "../test/fetchMock";
import { ACT_A, ACT_B, draftView } from "../test/generatedFixtures";
import { ReportDraftEditor } from "./ReportDraftEditor";

const GET = "GET /api/processes/p1/report-draft";
const ENTRY_A = `PUT /api/processes/p1/report-draft/entries/${ACT_A}`;

/** The draft the server holds: a write changes it and the next GET returns the new one. */
function server(initial: ReportDraftView = draftView()) {
  const state = { view: initial };
  const routes: Parameters<typeof mockFetch>[0] = {
    [GET]: () => ({ status: 200, body: state.view }),
  };
  return { state, routes };
}

function setup(initial: ReportDraftView = draftView(), extra: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const srv = server(initial);
  const mock = mockFetch({ ...srv.routes, ...extra });
  render(<ReportDraftEditor processId="p1" />);
  return { ...mock, ...srv, user: userEvent.setup() };
}

function section(title: string) {
  return screen.getByRole("region", { name: new RegExp(title) });
}

describe("UIG-02: uma seção por cartão", () => {
  it("mostra cada seção com a atividade, o texto e o selo da fonte (modelo, IA)", async () => {
    setup();
    const s = await screen.findByRole("region", { name: /1\.1 Ensino de graduação/ });
    expect(within(s).getByLabelText("Texto de Algoritmos")).toHaveValue("Disciplina Algoritmos, 60 h.");
    expect(within(s).getByLabelText("Texto de Redes")).toHaveValue("Disciplina Redes, 45 h.");
    const entries = within(s).getAllByRole("listitem");
    expect(within(entries[0]).getByText("Texto-modelo")).toBeInTheDocument();
    expect(within(entries[1]).getByText("Redigido pela IA")).toBeInTheDocument();
    expect(within(entries[0]).getByText(/I\.1 · Disciplina de graduação/)).toBeInTheDocument();
  });

  it("REL-11: a seção sem atividade aparece como vazia", async () => {
    setup();
    const s = await screen.findByRole("region", { name: /2 Pesquisa/ });
    expect(within(s).getByText(/Seção vazia/)).toBeInTheDocument();
    expect(within(s).queryByRole("textbox", { name: /Texto de/ })).not.toBeInTheDocument();
  });

  it("os avisos da seção saem em português, com o motivo da redação recusada", async () => {
    const view = draftView();
    view.sections[0].warnings = [{ code: "REDACAO_REJEITADA", message: "NUMERO,NOME" }];
    view.alerts = [{ code: "RASCUNHO_DESATUALIZADO", message: "Há atividades novas ou removidas desde a última edição do Relatório." }];
    setup(view);
    const s = await screen.findByRole("region", { name: /1\.1/ });
    expect(within(s).getByText(/foi recusada: ficou o texto-modelo \(número que não está na atividade, nome que não está na atividade\)/)).toBeInTheDocument();
    expect(screen.getByText(/rascunho do Relatório está desatualizado/)).toBeInTheDocument();
  });
});

describe("REL-07: editar e sair do campo grava a entrada", () => {
  it("grava com a versão lida do servidor e o selo passa a editado", async () => {
    const { state, calls, user } = setup(draftView({ version: 7 }), {
      [ENTRY_A]: (init) => {
        const body = JSON.parse(String(init?.body));
        state.view = draftView({ version: 8 });
        state.view.sections[0].entries[0] = { activity_id: ACT_A, text: body.text, source: "USUARIO", warnings: [] };
        return { status: 200, body: { ...state.view } };
      },
    });
    const box = await screen.findByLabelText("Texto de Algoritmos");
    await user.clear(box);
    await user.type(box, "Texto novo");
    await user.tab();
    await waitFor(() => expect(within(screen.getAllByRole("listitem")[0]).getByText("Editado")).toBeInTheDocument());
    const put = calls.find((c) => c.method === "PUT")!;
    expect(JSON.parse(String(put.init?.body))).toEqual({ expected_version: 7, text: "Texto novo" });
    expect(screen.getByLabelText("Texto de Algoritmos")).toHaveValue("Texto novo");
  });

  it("o rascunho que nunca foi salvo grava com a versão 0 que o GET mandou", async () => {
    const { calls, user } = setup(draftView({ version: 0, saved: false }), {
      [ENTRY_A]: { status: 200, body: draftView({ version: 1 }) },
    });
    const box = await screen.findByLabelText("Texto de Algoritmos");
    await user.type(box, "!");
    await user.tab();
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(JSON.parse(String(calls.find((c) => c.method === "PUT")!.init?.body)).expected_version).toBe(0);
  });

  it("sair do campo sem mudar o texto não grava nada", async () => {
    const { calls, user } = setup();
    const box = await screen.findByLabelText("Texto de Algoritmos");
    await user.click(box);
    await user.tab();
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
  });

  it("409 recarrega o rascunho, avisa e mantém o texto digitado", async () => {
    let reads = 0;
    const { calls, user } = setup(draftView(), {
      [GET]: () => ({ status: 200, body: draftView({ version: reads++ === 0 ? 4 : 5 }) }),
      [ENTRY_A]: { status: 409, body: { detail: "Versão desatualizada", code: "VERSAO_DESATUALIZADA" } },
    });
    const box = await screen.findByLabelText("Texto de Algoritmos");
    await user.type(box, "!");
    await user.tab();
    expect(await screen.findByRole("alert")).toHaveTextContent("Os dados mudaram desde que você abriu a tela");
    expect(calls.filter((c) => c.method === "GET")).toHaveLength(2);
    expect(screen.getByLabelText("Texto de Algoritmos")).toHaveValue("Disciplina Algoritmos, 60 h.!");
    // the next save carries the version that was reloaded
    expect(screen.getByRole("button", { name: "Salvar Algoritmos" })).toBeEnabled();
  });
});

describe("REL-07: o contador bloqueia acima de 20 000", () => {
  it("mostra o contador e não grava um texto acima do limite", async () => {
    const { calls } = setup();
    const box = await screen.findByLabelText("Texto de Algoritmos");
    fireEvent.change(box, { target: { value: "x".repeat(20_000) } });
    expect(screen.getAllByText(/20\s000 \/ 20\s000/)[0]).toBeInTheDocument();
    expect(box).not.toHaveAttribute("aria-invalid", "true");
    fireEvent.change(box, { target: { value: "x".repeat(20_001) } });
    expect(screen.getByText(/20\s001 \/ 20\s000/)).toBeInTheDocument();
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "Salvar Algoritmos" })).toBeDisabled();
    fireEvent.blur(box);
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
  });
});

describe("REL-08: mover a atividade para outra seção", () => {
  it("grava a escolha e a atividade passa para a seção escolhida", async () => {
    const { state, calls, user } = setup(draftView({ version: 4 }), {
      [`POST /api/processes/p1/report-draft/entries/${ACT_B}/move`]: () => {
        const moved = draftView({ version: 5 });
        const entry = moved.sections[0].entries.pop()!;
        moved.sections[1].entries.push(entry);
        moved.empty_sections = [];
        state.view = moved;
        return { status: 200, body: moved };
      },
    });
    await screen.findByLabelText("Texto de Redes");
    await user.selectOptions(screen.getByLabelText("Mover Redes para"), "2");
    await waitFor(() => expect(within(section("2 Pesquisa")).getByLabelText("Texto de Redes")).toBeInTheDocument());
    const post = calls.find((c) => c.method === "POST")!;
    expect(JSON.parse(String(post.init?.body))).toEqual({ expected_version: 4, section_key: "2" });
    expect(within(section("1.1")).queryByLabelText("Texto de Redes")).not.toBeInTheDocument();
    expect(within(section("2 Pesquisa")).queryByText(/Seção vazia/)).not.toBeInTheDocument();
  });
});

describe("REL-07: o texto livre da seção", () => {
  it("grava o texto da seção ao sair do campo", async () => {
    const { calls, user } = setup(draftView({ version: 4 }), {
      "PUT /api/processes/p1/report-draft/sections/2": { status: 200, body: draftView({ version: 5 }) },
    });
    const box = await screen.findByLabelText("Texto livre da seção 2");
    await user.type(box, "Projeto de pesquisa digitado");
    await user.tab();
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(JSON.parse(String(calls.find((c) => c.method === "PUT")!.init?.body))).toEqual({
      expected_version: 4,
      free_text: "Projeto de pesquisa digitado",
    });
  });
});
