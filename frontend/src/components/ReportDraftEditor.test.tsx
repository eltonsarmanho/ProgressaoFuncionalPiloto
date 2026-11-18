import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { ReportDraftView, WordingJob } from "../api/generated";
import { mockFetch } from "../test/fetchMock";
import { ACT_A, ACT_B, draftView, job } from "../test/generatedFixtures";
import { ReportDraftEditor } from "./ReportDraftEditor";

const GET = "GET /api/processes/p1/report-draft";
const WORDING = "GET /api/processes/p1/report-draft/wording";
const ENTRY_A = `PUT /api/processes/p1/report-draft/entries/${ACT_A}`;

afterEach(() => {
  vi.useRealTimers();
});

/** The draft and the wording jobs the server holds: a write changes them and the next GET returns the new ones. */
function server(initial: ReportDraftView = draftView(), jobs: WordingJob[] = []) {
  const state: { view: ReportDraftView; jobs: WordingJob[] } = { view: initial, jobs };
  const routes: Parameters<typeof mockFetch>[0] = {
    [GET]: () => ({ status: 200, body: state.view }),
    [WORDING]: () => ({ status: 200, body: state.jobs }),
  };
  return { state, routes };
}

function setup(
  initial: ReportDraftView = draftView(),
  extra: Parameters<typeof mockFetch>[0] = {},
  jobs: WordingJob[] = [],
) {
  setCsrfToken("tok");
  const srv = server(initial, jobs);
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
    expect(calls.filter((c) => `${c.method} ${c.path}` === GET)).toHaveLength(2);
    expect(screen.getByLabelText("Texto de Algoritmos")).toHaveValue("Disciplina Algoritmos, 60 h.!");
    // the next save carries the version that was reloaded
    expect(screen.getByRole("button", { name: "Salvar Algoritmos" })).toBeEnabled();
  });
});

describe("UIG-02, REL-07: o botão Salvar da entrada", () => {
  it("o clique, que tira o foco da caixa e a grava, não grava de novo com a versão velha nem mostra conflito", async () => {
    const stored: string[] = [];
    const { state, fn, calls, user } = setup(draftView({ version: 7 }), {
      [ENTRY_A]: (init) => {
        const body = JSON.parse(String(init?.body));
        // the server of the real system: a write with an old version is a conflict
        if (body.expected_version !== state.view.version) {
          return { status: 409, body: { detail: "Versão desatualizada", code: "VERSAO_DESATUALIZADA" } };
        }
        stored.push(body.text);
        state.view = draftView({ version: 8 });
        state.view.sections[0].entries[0] = { activity_id: ACT_A, text: body.text, source: "USUARIO", warnings: [] };
        return { status: 200, body: { ...state.view } };
      },
    });
    const box = await screen.findByLabelText("Texto de Algoritmos");
    await user.clear(box);
    await user.type(box, "Texto novo");

    // the write that leaves the box starts and is still in flight when the click arrives
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const original = fn.getMockImplementation()!;
    fn.mockImplementation(async (input, init) => {
      if ((init?.method ?? "GET").toUpperCase() === "PUT") await gate;
      return original(input, init);
    });
    await user.click(screen.getByRole("button", { name: "Salvar Algoritmos" }));
    release();

    await waitFor(() => expect(within(screen.getAllByRole("listitem")[0]).getByText("Editado")).toBeInTheDocument());
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1);
    expect(stored).toEqual(["Texto novo"]);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Texto de Algoritmos")).toHaveValue("Texto novo");
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

const ASK = "POST /api/processes/p1/report-draft/sections/1.1/wording";
const count = (calls: { method: string; path: string }[], key: string) =>
  calls.filter((c) => `${c.method} ${c.path}` === key).length;

/** Two sections that both have an activity, so both can be worded. */
function twoFilledSections(): ReportDraftView {
  const view = draftView();
  view.sections[1].entries = [{ activity_id: "a0000000-0000-0000-0000-000000000003", text: "Projeto Beta.", source: "MODELO", warnings: [] }];
  view.empty_sections = [];
  view.activities.push({ id: "a0000000-0000-0000-0000-000000000003", title: "Beta", group_number: 5, item_number: 1, event_date: null, academic_period: null });
  return view;
}

describe("UIG-02, REL-04: a redação recusada aparece uma vez", () => {
  it("com o aviso na entrada, o aviso da seção não repete a mesma frase", async () => {
    const view = draftView();
    view.sections[0].warnings = [{ code: "REDACAO_REJEITADA", message: "NUMERO" }];
    view.sections[0].entries[1].warnings = [{ code: "REDACAO_REJEITADA", message: "NUMERO" }];
    setup(view);
    const s = await screen.findByRole("region", { name: /1\.1/ });
    expect(within(s).getAllByText(/foi recusada: ficou o texto-modelo/)).toHaveLength(1);
    expect(within(within(s).getAllByRole("listitem")[1]).getByText(/foi recusada/)).toBeInTheDocument();
  });

  it("sem aviso em nenhuma entrada, o aviso da seção continua aparecendo", async () => {
    const view = draftView();
    view.sections[0].warnings = [{ code: "REDACAO_REJEITADA", message: "NUMERO" }];
    setup(view);
    const s = await screen.findByRole("region", { name: /1\.1/ });
    expect(within(s).getAllByText(/foi recusada: ficou o texto-modelo/)).toHaveLength(1);
  });
});

describe("UIG-08, REL-03: redação por seção em segundo plano", () => {
  it("pedir a redação mostra GERANDO na seção, desliga o botão e relê a versão do rascunho", async () => {
    const { state, calls, user } = setup(twoFilledSections(), {
      [ASK]: () => {
        state.view = { ...twoFilledSections(), version: 1 };
        state.jobs = [job()];
        return { status: 202, body: job() };
      },
    });
    const s = await screen.findByRole("region", { name: /1\.1/ });
    await user.click(within(s).getByRole("button", { name: "Pedir redação de 1.1" }));
    expect(await within(s).findByText("Gerando a redação…")).toBeInTheDocument();
    expect(within(s).getByRole("button", { name: "Pedir redação de 1.1" })).toBeDisabled();
    await waitFor(() => expect(count(calls, GET)).toBe(2));
    expect(count(calls, ASK)).toBe(1);
  });

  it("consulta a cada 3 s até PRONTO e recarrega o texto da seção", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { state, calls } = setup(twoFilledSections(), {}, [job()]);
    expect(await screen.findByText("Gerando a redação…")).toBeInTheDocument();
    expect(count(calls, WORDING)).toBe(1);

    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(count(calls, WORDING)).toBe(2);
    expect(screen.getByLabelText("Texto de Algoritmos")).toHaveValue("Disciplina Algoritmos, 60 h.");

    const done = twoFilledSections();
    done.sections[0].entries[0] = { activity_id: ACT_A, text: "Ministrou a disciplina Algoritmos, 60 h.", source: "IA", warnings: [] };
    state.view = done;
    state.jobs = [job({ state: "PRONTO", finished_at: "2026-11-18T10:00:09Z" })];
    await act(() => vi.advanceTimersByTimeAsync(3000));
    await waitFor(() => expect(screen.getByLabelText("Texto de Algoritmos")).toHaveValue("Ministrou a disciplina Algoritmos, 60 h."));
    expect(screen.queryByText("Gerando a redação…")).not.toBeInTheDocument();

    const before = count(calls, WORDING);
    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(count(calls, WORDING)).toBe(before);
  });

  it("ao terminar, o que foi digitado e não salvo em outra seção continua na caixa", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { state } = setup(twoFilledSections(), {}, [job()]);
    await screen.findByText("Gerando a redação…");
    const other = screen.getByLabelText("Texto de Beta");
    fireEvent.change(other, { target: { value: "Projeto Beta, ainda digitando" } });

    state.jobs = [job({ state: "PRONTO" })];
    await act(() => vi.advanceTimersByTimeAsync(3000));
    await waitFor(() => expect(screen.queryByText("Gerando a redação…")).not.toBeInTheDocument());
    expect(screen.getByLabelText("Texto de Beta")).toHaveValue("Projeto Beta, ainda digitando");
  });

  it("enquanto uma seção gera, as demais seções seguem editáveis e com o botão ligado", async () => {
    setup(twoFilledSections(), {}, [job()]);
    await screen.findByText("Gerando a redação…");
    expect(screen.getByRole("button", { name: "Pedir redação de 1.1" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Pedir redação de 2" })).toBeEnabled();
    expect(screen.getByLabelText("Texto de Beta")).toBeEnabled();
    expect(screen.getByLabelText("Texto livre da seção 2")).toBeEnabled();
  });

  it("409 REDACAO_EM_ANDAMENTO mostra a mensagem em português", async () => {
    const { user } = setup(twoFilledSections(), {
      [ASK]: { status: 409, body: { detail: "Redação em andamento", code: "REDACAO_EM_ANDAMENTO" } },
    });
    await user.click(await screen.findByRole("button", { name: "Pedir redação de 1.1" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Já há uma redação desta seção em andamento.");
  });

  it("FALHOU mostra o aviso com o motivo e permite pedir de novo", async () => {
    const { state, calls, user } = setup(
      twoFilledSections(),
      {
        [ASK]: () => {
          state.jobs = [job({ id: "j2" })];
          return { status: 202, body: job({ id: "j2" }) };
        },
      },
      [job({ state: "FALHOU", error_code: "INTERROMPIDA" })],
    );
    const s = await screen.findByRole("region", { name: /1\.1/ });
    expect(await within(s).findByText(/A redação falhou: O servidor reiniciou durante o trabalho/)).toBeInTheDocument();
    const button = within(s).getByRole("button", { name: "Pedir redação de 1.1" });
    expect(button).toBeEnabled();
    await user.click(button);
    expect(await within(s).findByText("Gerando a redação…")).toBeInTheDocument();
    expect(count(calls, ASK)).toBe(1);
  });

  it("REDACAO_INDISPONIVEL e REDACAO_REJEITADA, que chegam com a seção recarregada, saem em português", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { state } = setup(twoFilledSections(), {}, [job()]);
    await screen.findByText("Gerando a redação…");
    const done = twoFilledSections();
    done.sections[0].warnings = [{ code: "REDACAO_INDISPONIVEL", message: "" }];
    done.sections[0].entries[1].warnings = [{ code: "REDACAO_REJEITADA", message: "DATA" }];
    state.view = done;
    state.jobs = [job({ state: "PRONTO" })];
    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(await screen.findByText("A IA não está disponível agora: ficou o texto-modelo")).toBeInTheDocument();
    expect(screen.getByText(/foi recusada: ficou o texto-modelo \(data que não está na atividade\)/)).toBeInTheDocument();
  });
});
