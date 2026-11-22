import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../auth/AuthContext";
import type { BoardView, ChecklistItem } from "../api/board";
import { setCsrfToken } from "../api/client";
import type { ConclusionPreview, GeneratedDocument } from "../api/generated";
import type { Process, ProcessStatus } from "../api/types";
import { board, checklist, requestSettings } from "../test/boardFixtures";
import { ME, mockFetch } from "../test/fetchMock";
import { generated, preview } from "../test/generatedFixtures";
import { ProcessDossier } from "./ProcessDossier";

const BOARD = "GET /api/processes/p1/board";
const DOSSIER = "GET /api/processes/p1/dossier";
const REQ_LIST = "GET /api/processes/p1/generated-documents?kind=REQUERIMENTO";
const ASK = "POST /api/processes/p1/generated-documents";
const CITY = "PUT /api/processes/p1/request-settings";
const READ_ONLY_REASON = "O processo está concluído ou arquivado e não aceita alterações.";
const CONCLUDE = "Concluir e excluir documentos de entrada";
const DRAFT_TEXT = "Inicie o processo na Etapa 1 para poder concluir.";

afterEach(() => {
  vi.useRealTimers();
});

function process(status: ProcessStatus, version = 7): Process {
  return { id: "p1", status, version } as Process;
}

const requestRow = (over: Partial<GeneratedDocument> = {}) => generated({ id: "req1", kind: "REQUERIMENTO", ...over });

type State = { status: ProcessStatus; view: BoardView; rows: GeneratedDocument[]; items: ChecklistItem[]; preview: ConclusionPreview };

function setup(status: ProcessStatus = "EM_ANDAMENTO", init: Partial<State> = {}, extra: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const state: State = { status, view: board(), rows: [], items: checklist(), preview: preview(), ...init };
  const mock = mockFetch({
    "GET /api/processes/p1": () => ({ status: 200, body: process(state.status) }),
    [BOARD]: () => ({ status: 200, body: state.view }),
    [REQ_LIST]: () => ({ status: 200, body: state.rows }),
    [DOSSIER]: () => ({ status: 200, body: state.items }),
    "GET /api/processes/p1/conclusion": () => ({ status: 200, body: state.preview }),
    ...extra,
  });
  render(
    <MemoryRouter initialEntries={["/processos/p1/dossie"]}>
      <Routes>
        <Route path="processos/:id/dossie" element={<ProcessDossier />} />
      </Routes>
    </MemoryRouter>,
  );
  return { ...mock, state, user: userEvent.setup() };
}

const count = (calls: { method: string; path: string }[], key: string) => calls.filter((c) => `${c.method} ${c.path}` === key).length;
const block = (name: string) => screen.findByRole("region", { name });
const stateOf = async (title: string) => {
  const list = await screen.findByRole("list", { name: "Ordem de entrega do dossiê" });
  const li = within(list).getAllByRole("listitem").find((item) => within(item).queryByText(title) !== null)!;
  return within(li).getByTestId("checklist-state").textContent;
};

describe("BNAV-01, REQ-01, DOS-02: a página da Etapa 7", () => {
  it("mostra a navegação com a Etapa 7 atual, o campo Cidade, o bloco do Requerimento e o checklist", async () => {
    setup();
    expect(screen.getByRole("heading", { name: "Etapa 7 · Requerimento e dossiê" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getAllByRole("listitem")[6]).toHaveAttribute("aria-current", "step");
    const city = await block("Cidade do Requerimento");
    expect(await within(city).findByLabelText("Cidade")).toHaveValue("");
    const request = await block("Requerimento");
    expect(await within(request).findByRole("button", { name: "Gerar Requerimento" })).toBeEnabled();
    const list = await screen.findByRole("list", { name: "Ordem de entrega do dossiê" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(9);
  });

  it("a rota /processos/p1/dossie existe no aplicativo", async () => {
    setCsrfToken("tok");
    mockFetch({
      "GET /api/auth/me": { status: 200, body: ME },
      "GET /api/processes/p1": { status: 200, body: process("EM_ANDAMENTO") },
      [BOARD]: { status: 200, body: board() },
      [REQ_LIST]: { status: 200, body: [] },
      [DOSSIER]: { status: 200, body: checklist() },
    });
    render(
      <MemoryRouter initialEntries={["/processos/p1/dossie"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByRole("heading", { name: "Etapa 7 · Requerimento e dossiê" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Etapa 6 · Banca e Parecer" })).toHaveAttribute("href", "/processos/p1/banca");
  });
});

describe("REQ-05, REQ-06: a cidade do Requerimento", () => {
  it("digitar a cidade e salvar envia PUT /request-settings com a cidade e a versão", async () => {
    const saved = requestSettings({ city: "Belém", version: 1 });
    const { calls, user } = setup("EM_ANDAMENTO", {}, { [CITY]: { status: 200, body: saved } });
    const input = await screen.findByLabelText("Cidade");
    await user.type(input, "Belém");
    await user.click(screen.getByRole("button", { name: "Salvar cidade" }));
    await waitFor(() => expect(count(calls, CITY)).toBe(1));
    expect(JSON.parse(String(calls.find((c) => `${c.method} ${c.path}` === CITY)!.init?.body))).toEqual({ city: "Belém", expected_version: 0 });
    await waitFor(() => expect(screen.getByLabelText("Cidade")).toHaveValue("Belém"));
  });

  it("uma cidade já salva aparece no campo e a próxima gravação leva a versão dela", async () => {
    const { calls, user } = setup("EM_ANDAMENTO", { view: board({ request_settings: requestSettings({ city: "Belém", version: 2 }) }) }, {
      [CITY]: { status: 200, body: requestSettings({ city: "Santarém", version: 3 }) },
    });
    const input = await screen.findByLabelText("Cidade");
    await waitFor(() => expect(input).toHaveValue("Belém"));
    await user.clear(input);
    await user.type(input, "Santarém");
    await user.click(screen.getByRole("button", { name: "Salvar cidade" }));
    await waitFor(() => expect(count(calls, CITY)).toBe(1));
    expect(JSON.parse(String(calls.find((c) => `${c.method} ${c.path}` === CITY)!.init?.body))).toEqual({ city: "Santarém", expected_version: 2 });
  });

  it("apagar a cidade e salvar envia city nulo (o Requerimento usa a linha em branco)", async () => {
    const { calls, user } = setup("EM_ANDAMENTO", { view: board({ request_settings: requestSettings({ city: "Belém", version: 2 }) }) }, {
      [CITY]: { status: 200, body: requestSettings({ city: null, version: 3 }) },
    });
    const input = await screen.findByLabelText("Cidade");
    await waitFor(() => expect(input).toHaveValue("Belém"));
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Salvar cidade" }));
    await waitFor(() => expect(count(calls, CITY)).toBe(1));
    expect(JSON.parse(String(calls.find((c) => `${c.method} ${c.path}` === CITY)!.init?.body))).toEqual({ city: null, expected_version: 2 });
  });

  it("422 de city mostra o erro junto do campo", async () => {
    const { user } = setup("EM_ANDAMENTO", {}, {
      [CITY]: { status: 422, body: { detail: [{ field: "city", code: "TEXTO_LONGO", message: "A cidade tem no máximo 100 caracteres." }] } },
    });
    await user.type(await screen.findByLabelText("Cidade"), "X");
    await user.click(screen.getByRole("button", { name: "Salvar cidade" }));
    const field = await screen.findByLabelText("Cidade");
    await waitFor(() => expect(field).toHaveAttribute("aria-invalid", "true"));
    expect(screen.getByText("A cidade tem no máximo 100 caracteres.")).toBeInTheDocument();
  });

  it("409 de versão mostra o texto de recarregar e lê a banca de novo", async () => {
    const { calls, user } = setup("EM_ANDAMENTO", {}, { [CITY]: { status: 409, body: { detail: "x", code: "VERSAO_DESATUALIZADA" } } });
    await user.type(await screen.findByLabelText("Cidade"), "X");
    await user.click(screen.getByRole("button", { name: "Salvar cidade" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Os dados foram alterados por outra pessoa; recarregue");
    await waitFor(() => expect(count(calls, BOARD)).toBe(2));
  });
});

describe("REQ-01, DOS-02: gerar o Requerimento atualiza o checklist sem recarregar a página", () => {
  it("'Gerar Requerimento' pede o tipo REQUERIMENTO e, quando a versão fica PRONTO, o item passa a Gerado", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const running = requestRow({ state: "GERANDO", version_number: null, files: [], finished_at: null });
    const { state, calls, user } = setup("EM_ANDAMENTO", {}, {
      [ASK]: () => {
        state.rows = [running];
        return { status: 202, body: running };
      },
    });
    expect(await stateOf("Requerimento")).toBe("Pendente");
    await user.click(await screen.findByRole("button", { name: "Gerar Requerimento" }));
    await waitFor(() => expect(count(calls, ASK)).toBe(1));
    expect(JSON.parse(String(calls.find((c) => `${c.method} ${c.path}` === ASK)!.init?.body))).toEqual({ kind: "REQUERIMENTO" });
    expect(await screen.findByText("Gerando…")).toBeInTheDocument();
    expect(await stateOf("Requerimento")).toBe("Pendente");

    state.rows = [requestRow()];
    state.items = checklist({ REQUERIMENTO: { state: "GERADO", version_number: 1, generation_id: "req1" } });
    await act(() => vi.advanceTimersByTimeAsync(3000));
    await waitFor(async () => expect(await stateOf("Requerimento")).toBe("Gerado"));
    expect(screen.getAllByRole("link", { name: "Baixar Requerimento versão 1 em PDF" })).not.toHaveLength(0);
    expect(count(calls, "GET /api/processes/p1")).toBe(1);
  });
});

describe("UIG-09: Concluir o processo, agora na Etapa 7", () => {
  it("só o processo EM_ANDAMENTO oferece o botão, que abre a confirmação", async () => {
    const { user } = setup("EM_ANDAMENTO");
    await block("Requerimento");
    await user.click(await screen.findByRole("button", { name: CONCLUDE }));
    const dialog = await screen.findByRole("dialog", { name: CONCLUDE });
    expect(await within(dialog).findByText(/serão excluídos de forma irreversível/)).toBeInTheDocument();
  });

  it.each(["RASCUNHO", "ARQUIVADO"] as const)("o processo %s não oferece a conclusão", async (status) => {
    setup(status);
    await block("Requerimento");
    expect(screen.queryByRole("button", { name: CONCLUDE })).not.toBeInTheDocument();
  });

  it("ao concluir, a página recarrega o processo: o botão some e o Requerimento deixa de ser gerado", async () => {
    const { state, calls, user } = setup("EM_ANDAMENTO", {}, {
      "POST /api/processes/p1/conclusion": {
        status: 200,
        body: { status: "CONCLUIDO", arquivos_removidos: 3, arquivos_pendentes: 0, bytes_liberados: 5_242_880, alertas: [] },
      },
    });
    const request = await block("Requerimento");
    await waitFor(() => expect(within(request).getByRole("button", { name: "Gerar Requerimento" })).toBeEnabled());
    await user.click(await screen.findByRole("button", { name: CONCLUDE }));
    const dialog = await screen.findByRole("dialog");
    state.status = "CONCLUIDO";
    await user.click(await within(dialog).findByLabelText(/Confirmo a exclusão irreversível/));
    await user.click(within(dialog).getByRole("button", { name: "Concluir e excluir" }));
    expect(await within(dialog).findByText("Processo concluído.")).toBeInTheDocument();
    await waitFor(() => expect(count(calls, "GET /api/processes/p1")).toBe(2));
    await waitFor(() => expect(within(screen.getByRole("region", { name: "Requerimento" })).getByRole("button", { name: "Gerar Requerimento" })).toBeDisabled());
    expect(screen.queryByRole("button", { name: CONCLUDE })).not.toBeInTheDocument();
  });

  it("DOS-07: a confirmação lista como aviso os pendentes da banca e não bloqueia a conclusão", async () => {
    const { calls, user } = setup("EM_ANDAMENTO", { preview: preview({ pending_board: ["REQUERIMENTO", "PORTARIA_BANCA", "PARECER"] }) }, {
      "POST /api/processes/p1/conclusion": {
        status: 200,
        body: { status: "CONCLUIDO", arquivos_removidos: 3, arquivos_pendentes: 0, bytes_liberados: 5_242_880, alertas: [] },
      },
    });
    await user.click(await screen.findByRole("button", { name: CONCLUDE }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/Ainda não gerados ou registrados:/)).toHaveTextContent("Requerimento, Portaria da banca, Parecer");
    await user.click(within(dialog).getByLabelText(/Confirmo a exclusão irreversível/));
    const confirm = within(dialog).getByRole("button", { name: "Concluir e excluir" });
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    await waitFor(() => expect(count(calls, "POST /api/processes/p1/conclusion")).toBe(1));
  });
});

describe("CAINI-10, CAINI-11: a Etapa 7 explica a conclusão conforme o status", () => {
  it("CAINI-10: em rascunho mostra o título, o texto, o link para a Etapa 1 e nenhum botão de concluir", async () => {
    setup("RASCUNHO");
    await block("Requerimento");
    expect(await screen.findByRole("heading", { name: "Concluir o processo" })).toBeInTheDocument();
    expect(screen.getByText(DRAFT_TEXT)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para a Etapa 1" })).toHaveAttribute("href", "/processos/p1");
    expect(screen.queryByRole("button", { name: CONCLUDE })).not.toBeInTheDocument();
  });

  it("CAINI-11: em andamento mostra o botão de concluir e não o texto de rascunho", async () => {
    setup("EM_ANDAMENTO");
    await block("Requerimento");
    expect(await screen.findByRole("heading", { name: "Concluir o processo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: CONCLUDE })).toBeInTheDocument();
    expect(screen.queryByText(DRAFT_TEXT)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ir para a Etapa 1" })).not.toBeInTheDocument();
  });

  it.each(["CONCLUIDO", "ARQUIVADO"] as const)("CAINI-10, CAINI-11: com o processo %s não mostra o botão nem o texto de rascunho", async (status) => {
    setup(status);
    await block("Requerimento");
    expect(screen.queryByRole("button", { name: CONCLUDE })).not.toBeInTheDocument();
    expect(screen.queryByText(DRAFT_TEXT)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ir para a Etapa 1" })).not.toBeInTheDocument();
  });
});

describe("BNAV-02: processo arquivado ou concluído", () => {
  it.each<ProcessStatus>(["ARQUIVADO", "CONCLUIDO"])(
    "%s: aviso de somente leitura; cidade, geração e marcas desligadas com o motivo; download mantido",
    async (status) => {
      setup(status, {
        rows: [requestRow()],
        items: checklist({ REQUERIMENTO: { state: "GERADO", version_number: 1, generation_id: "req1" } }),
      });
      expect(await screen.findByText(/só podem ser lidos/)).toBeInTheDocument();
      const city = await block("Cidade do Requerimento");
      expect(await within(city).findByLabelText("Cidade")).toBeDisabled();
      expect(within(city).getByRole("button", { name: "Salvar cidade" })).toBeDisabled();
      expect(within(city).getByText(READ_ONLY_REASON)).toBeInTheDocument();
      const request = await block("Requerimento");
      expect(await within(request).findByRole("button", { name: "Gerar Requerimento" })).toBeDisabled();
      expect(within(request).getByText(READ_ONLY_REASON)).toBeInTheDocument();
      expect(await within(request).findByRole("link", { name: "Baixar Requerimento versão 1 em PDF" })).toHaveAttribute(
        "href",
        "/api/generated-documents/req1/files/pdf",
      );
      const dossier = await block("Dossiê");
      const boxes = await within(dossier).findAllByRole("checkbox");
      expect(boxes).toHaveLength(3);
      for (const box of boxes) expect(box).toBeDisabled();
      expect(within(dossier).getByText(READ_ONLY_REASON)).toBeInTheDocument();
    },
  );

  it("processo em andamento não mostra o aviso de somente leitura nem o motivo", async () => {
    setup("EM_ANDAMENTO");
    await block("Requerimento");
    await screen.findByRole("list", { name: "Ordem de entrega do dossiê" });
    expect(screen.queryByText(/só podem ser lidos/)).not.toBeInTheDocument();
    expect(screen.queryByText(READ_ONLY_REASON)).not.toBeInTheDocument();
  });
});
