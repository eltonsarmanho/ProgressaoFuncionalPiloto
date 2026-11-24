import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../auth/AuthContext";
import type { BoardView } from "../api/board";
import { setCsrfToken } from "../api/client";
import type { GeneratedDocument } from "../api/generated";
import type { Process, ProcessStatus } from "../api/types";
import { ME, mockFetch } from "../test/fetchMock";
import { board, ordinance } from "../test/boardFixtures";
import { generated } from "../test/generatedFixtures";
import { ProcessBoard } from "./ProcessBoard";

const BOARD = "GET /api/processes/p1/board";
const PARECER_LIST = "GET /api/processes/p1/generated-documents?kind=PARECER";
const ASK = "POST /api/processes/p1/generated-documents";
const READ_ONLY_REASON = "O processo está concluído ou arquivado e não aceita alterações.";

afterEach(() => {
  vi.useRealTimers();
});

function process(status: ProcessStatus): Process {
  return { id: "p1", status, version: 7 } as Process;
}

const opinionRow = (over: Partial<GeneratedDocument> = {}) => generated({ id: "par1", kind: "PARECER", ...over });

function setup(status: ProcessStatus = "EM_ANDAMENTO", view: BoardView = board(), rows: GeneratedDocument[] = [], extra: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const state = { view, rows };
  const mock = mockFetch({
    "GET /api/processes/p1": { status: 200, body: process(status) },
    [BOARD]: () => ({ status: 200, body: state.view }),
    [PARECER_LIST]: () => ({ status: 200, body: state.rows }),
    ...extra,
  });
  render(
    <MemoryRouter initialEntries={["/processos/p1/banca"]}>
      <Routes>
        <Route path="processos/:id/banca" element={<ProcessBoard />} />
      </Routes>
    </MemoryRouter>,
  );
  return { ...mock, state, user: userEvent.setup() };
}

const count = (calls: { method: string; path: string }[], key: string) => calls.filter((c) => `${c.method} ${c.path}` === key).length;

describe("BNAV-01, PORT-01, PAR-01, PAR-02: a página da Etapa 6", () => {
  it("mostra a navegação com a Etapa 6 atual, o bloco da portaria e o bloco do Parecer com 'Gerar Parecer'", async () => {
    setup();
    expect(screen.getByRole("heading", { name: "Etapa 6 · Banca e Parecer" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getAllByRole("listitem")[5]).toHaveAttribute("aria-current", "step");
    const portaria = await screen.findByRole("region", { name: "Portaria da banca" });
    expect(await within(portaria).findByLabelText("Número da portaria")).toHaveValue("123/2026");
    expect(within(portaria).getByDisplayValue("Ana Sintética")).toBeInTheDocument();
    const minuta = await screen.findByRole("region", { name: "Minuta do Parecer" });
    expect(await within(minuta).findByRole("radio", { name: "Favorável" })).not.toBeChecked();
    expect(within(minuta).getByRole("radio", { name: "Desfavorável" })).not.toBeChecked();
    const parecer = await screen.findByRole("region", { name: "Parecer" });
    expect(await within(parecer).findByRole("button", { name: "Gerar Parecer" })).toBeEnabled();
  });

  it("a rota /processos/p1/banca existe no aplicativo", async () => {
    setCsrfToken("tok");
    mockFetch({
      "GET /api/auth/me": { status: 200, body: ME },
      "GET /api/processes/p1": { status: 200, body: process("EM_ANDAMENTO") },
      [BOARD]: { status: 200, body: board() },
      [PARECER_LIST]: { status: 200, body: [] },
    });
    render(
      <MemoryRouter initialEntries={["/processos/p1/banca"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "Etapa 6 · Banca e Parecer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Etapa 5 · Documentos gerados" })).toHaveAttribute("href", "/processos/p1/gerados");
  });
});

describe("PORT-02, PORT-07: a leitura em andamento", () => {
  it("com a leitura PENDENTE consulta de novo a cada 3 s até LIDA e para", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const queued = board({ ordinance: ordinance({ reading_state: "PENDENTE", number: null, members: [] }) });
    const { state, calls } = setup("EM_ANDAMENTO", queued);
    expect(await screen.findByText("Na fila de leitura")).toBeInTheDocument();
    expect(count(calls, BOARD)).toBe(1);

    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(count(calls, BOARD)).toBe(2);
    expect(screen.getByText("Na fila de leitura")).toBeInTheDocument();

    state.view = board({ ordinance: ordinance({ version: 4 }) });
    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(count(calls, BOARD)).toBe(3);
    expect(await screen.findByText("Portaria lida")).toBeInTheDocument();
    expect(screen.getByLabelText("Número da portaria")).toHaveValue("123/2026");
    expect(screen.getByDisplayValue("Bruno Fictício")).toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(count(calls, BOARD)).toBe(3);
  });

  it("a leitura que falhou não consulta de novo e mostra o motivo com 'Ler de novo'", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { calls } = setup("EM_ANDAMENTO", board({ ordinance: ordinance({ reading_state: "FALHOU", reading_code: "IA_INDISPONIVEL" }) }));
    expect(await screen.findByRole("button", { name: "Ler de novo" })).toBeEnabled();
    expect(screen.getByRole("alert")).toHaveTextContent("A IA não está disponível agora.");
    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(count(calls, BOARD)).toBe(1);
  });
});

describe("PAR-02, PAR-07..10, PAR-14: gerar o Parecer", () => {
  it("'Gerar Parecer' pede o tipo PARECER", async () => {
    const { calls, user } = setup("EM_ANDAMENTO", board(), [], {
      [ASK]: { status: 202, body: opinionRow({ state: "GERANDO", version_number: null, files: [] }) },
    });
    await user.click(await screen.findByRole("button", { name: "Gerar Parecer" }));
    await waitFor(() => expect(count(calls, ASK)).toBe(1));
    expect(JSON.parse(String(calls.find((c) => `${c.method} ${c.path}` === ASK)!.init?.body))).toEqual({ kind: "PARECER" });
  });

  it("PAR-07: com a conclusão ausente mostra a mensagem de CONCLUSAO_AUSENTE", async () => {
    const { user } = setup("EM_ANDAMENTO", board(), [], {
      [ASK]: {
        status: 422,
        body: { detail: [{ field: "geracao", code: "CONCLUSAO_AUSENTE", message: "Escolha a conclusão do Parecer antes de gerar." }] },
      },
    });
    await user.click(await screen.findByRole("button", { name: "Gerar Parecer" }));
    expect(await screen.findByText("Escolha a conclusão do Parecer antes de gerar.")).toBeInTheDocument();
  });

  it("PAR-10: com a pontuação mudada mostra a mensagem de TABELA_DESATUALIZADA", async () => {
    const { user } = setup("EM_ANDAMENTO", board(), [], {
      [ASK]: {
        status: 422,
        body: {
          detail: [
            { field: "geracao", code: "TABELA_DESATUALIZADA", message: "A pontuação mudou depois da última Tabela; gere a Tabela de novo" },
          ],
        },
      },
    });
    await user.click(await screen.findByRole("button", { name: "Gerar Parecer" }));
    expect(await screen.findByText("A pontuação mudou depois da última Tabela; gere a Tabela de novo")).toBeInTheDocument();
  });

  it("PAR-14: a lista de versões do Parecer traz os links de DOCX e PDF de cada versão pronta", async () => {
    setup("EM_ANDAMENTO", board(), [opinionRow({ id: "par2", version_number: 2 }), opinionRow({ id: "par1", version_number: 1 })]);
    const history = await screen.findByRole("list", { name: "Versões geradas" });
    expect(within(history).getAllByRole("listitem")).toHaveLength(2);
    expect(within(history).getByRole("link", { name: "Baixar Parecer versão 2 em DOCX" })).toHaveAttribute("href", "/api/generated-documents/par2/files/docx");
    expect(within(history).getByRole("link", { name: "Baixar Parecer versão 2 em PDF" })).toHaveAttribute("href", "/api/generated-documents/par2/files/pdf");
    expect(within(history).getByRole("link", { name: "Baixar Parecer versão 1 em PDF" })).toHaveAttribute("href", "/api/generated-documents/par1/files/pdf");
  });
});

describe("BNAV-02: processo arquivado ou concluído", () => {
  it.each<ProcessStatus>(["ARQUIVADO", "CONCLUIDO"])("%s: aviso de somente leitura, envio, gravação e geração desligados com o motivo, download mantido", async (status) => {
    setup(status, board(), [opinionRow()]);
    expect(await screen.findByText(/só podem ser lidas/)).toBeInTheDocument();
    const portaria = await screen.findByRole("region", { name: "Portaria da banca" });
    await within(portaria).findByLabelText("Número da portaria");
    expect(within(portaria).getByLabelText("Arquivo da portaria")).toBeDisabled();
    expect(within(portaria).getByLabelText("Número da portaria")).toBeDisabled();
    expect(within(portaria).getByRole("button", { name: "Salvar dados da portaria" })).toBeDisabled();
    expect(within(portaria).getByText(READ_ONLY_REASON)).toBeInTheDocument();
    const minuta = await screen.findByRole("region", { name: "Minuta do Parecer" });
    expect(await within(minuta).findByRole("radio", { name: "Favorável" })).toBeDisabled();
    expect(within(minuta).getByRole("button", { name: "Salvar minuta do Parecer" })).toBeDisabled();
    expect(within(minuta).getByText(READ_ONLY_REASON)).toBeInTheDocument();
    const parecer = await screen.findByRole("region", { name: "Parecer" });
    const generate = await within(parecer).findByRole("button", { name: "Gerar Parecer" });
    expect(generate).toBeDisabled();
    expect(within(parecer).getByText(READ_ONLY_REASON)).toBeInTheDocument();
    expect(await within(parecer).findByRole("link", { name: "Baixar Parecer versão 1 em PDF" })).toHaveAttribute("href", "/api/generated-documents/par1/files/pdf");
  });

  it("processo em andamento não mostra o aviso de somente leitura", async () => {
    setup("EM_ANDAMENTO");
    await screen.findByRole("region", { name: "Portaria da banca" });
    expect(screen.queryByText(/só podem ser lidas/)).not.toBeInTheDocument();
    expect(screen.queryByText(READ_ONLY_REASON)).not.toBeInTheDocument();
  });
});
