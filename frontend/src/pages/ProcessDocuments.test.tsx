import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { DocumentDetail, DocumentSummary } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { ProcessDocuments } from "./ProcessDocuments";

function doc(over: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "d1", process_id: "p1", original_name: "ata.pdf", mime: "application/pdf", size_bytes: 2048, sha256: "a".repeat(64),
    page_count: 3, status: "PROCESSADO", status_code: null, manual_type: null, manual_category: null, suggested_type: "ATA_DEFESA",
    suggested_category: "BANCA_MESTRADO", confidence: "0.90", uploaded_by: "u1", uploaded_at: null, updated_at: null, version: 1, ...over,
  };
}

const DETAIL: DocumentDetail = {
  ...doc(),
  pages: [{ page_number: 1, method: "TEXTO", char_count: 10, ocr_confidence: null, text: "Texto da ata" }],
  run: null,
  alerts: [],
  activities: [],
};

const SCORING_ROUTES = {
  "GET /api/processes/p1/scoring/table": { status: 200, body: { chosen: null, suggested: null, alerts: [] } },
};

function LocationProbe() {
  return <span data-testid="search">{useLocation().search}</span>;
}

function renderPage(routes: Parameters<typeof mockFetch>[0], path = "/processos/p1/documentos") {
  setCsrfToken("tok");
  const mock = mockFetch({ ...SCORING_ROUTES, ...routes });
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="processos/:id/documentos" element={<ProcessDocuments />} />
      </Routes>
      <LocationProbe />
    </MemoryRouter>,
  );
  return { ...mock, user: userEvent.setup() };
}

const LIST = "GET /api/processes/p1/documents";
const listCalls = (calls: { method: string; path: string }[]) => calls.filter((c) => `${c.method} ${c.path}` === LIST).length;

afterEach(() => {
  vi.useRealTimers();
});

describe("TELA-01 / TELA-02: página da Etapa 2", () => {
  it("mostra a navegação com a Etapa 2 atual, a área de envio e a lista dos documentos", async () => {
    renderPage({ [LIST]: { status: 200, body: [doc()] } });
    expect(await screen.findByText("ata.pdf", { selector: "td" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Etapa 2 · Documentos" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getAllByRole("listitem")[1]).toHaveAttribute("aria-current", "step");
    expect(screen.getByLabelText(/Selecionar arquivos/)).toBeInTheDocument();
  });

  it("erro ao carregar a lista aparece como alerta", async () => {
    renderPage({ [LIST]: { status: 404, body: { detail: "Processo não encontrado" } } });
    expect(await screen.findByRole("alert")).toHaveTextContent("Processo não encontrado");
  });
});

describe("TELA-03: atualização automática a cada 3 s", () => {
  it("recarrega enquanto há PENDENTE ou PROCESSANDO e para quando não há (relógio simulado)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let call = 0;
    const { calls } = renderPage({
      [LIST]: () => {
        call += 1;
        const status = call === 1 ? "PENDENTE" : call === 2 ? "PROCESSANDO" : "PROCESSADO";
        return { status: 200, body: [doc({ status })] };
      },
    });
    expect(await screen.findByText("Pendente")).toBeInTheDocument();
    expect(listCalls(calls)).toBe(1);

    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(await screen.findByText("Processando")).toBeInTheDocument();
    expect(listCalls(calls)).toBe(2);

    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(await screen.findByText("Processado")).toBeInTheDocument();
    expect(listCalls(calls)).toBe(3);

    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(listCalls(calls)).toBe(3);
  });

  it("sem documento pendente ou em processamento não recarrega sozinha", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { calls } = renderPage({ [LIST]: { status: 200, body: [doc()] } });
    expect(await screen.findByText("ata.pdf", { selector: "td" })).toBeInTheDocument();
    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(listCalls(calls)).toBe(1);
  });
});

describe("TELA-04: ações recarregam a lista", () => {
  it("um envio concluído recarrega a lista", async () => {
    let listed = 0;
    const { calls, user } = renderPage({
      [LIST]: () => {
        listed += 1;
        return { status: 200, body: listed === 1 ? [] : [doc({ original_name: "novo.pdf" })] };
      },
      "POST /api/processes/p1/documents": {
        status: 201,
        body: [{ original_name: "novo.pdf", status_code: 201, document: doc(), existing_document_id: null, field: null, code: null, message: null }],
      },
    });
    await screen.findByText("Nenhum documento enviado neste processo.");
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), new File(["%PDF"], "novo.pdf", { type: "application/pdf" }));
    expect(await screen.findByText("novo.pdf", { selector: "td" })).toBeInTheDocument();
    expect(listCalls(calls)).toBe(2);
  });

  it("reprocessar chama a API e recarrega a lista", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [doc()] },
      "POST /api/documents/d1/reprocess": { status: 202, body: doc({ status: "PENDENTE" }) },
    });
    await user.click(await screen.findByRole("button", { name: "Reprocessar ata.pdf" }));
    await waitFor(() => expect(listCalls(calls)).toBe(2));
  });

  it("excluir sem justificativa chama a API e recarrega a lista", async () => {
    const { calls, user } = renderPage({
      [LIST]: { status: 200, body: [doc()] },
      "DELETE /api/documents/d1": { status: 204 },
    });
    await user.click(await screen.findByRole("button", { name: "Excluir ata.pdf" }));
    expect(screen.queryByLabelText("Justificativa da exclusão")).not.toBeInTheDocument();
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(listCalls(calls)).toBe(2));
    expect(calls.some((c) => c.method === "DELETE" && c.path === "/api/documents/d1")).toBe(true);
  });

  it("visualizar abre o visualizador numa janela com o detalhe e põe ?documento= na URL", async () => {
    const { user } = renderPage({
      [LIST]: { status: 200, body: [doc()] },
      "GET /api/documents/d1": { status: 200, body: DETAIL },
    });
    await user.click(await screen.findByRole("button", { name: "Visualizar ata.pdf" }));

    const dialog = await screen.findByRole("dialog", { name: "ata.pdf" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(await within(dialog).findByText("Texto da ata")).toBeInTheDocument();
    expect(within(dialog).getByTitle("Documento ata.pdf")).toBeInTheDocument();
    expect(screen.getByTestId("search")).toHaveTextContent("?documento=d1");
  });

  it("Fechar e Esc fecham a janela, tiram ?documento= da URL e devolvem o foco ao botão", async () => {
    const { user } = renderPage({
      [LIST]: { status: 200, body: [doc()] },
      "GET /api/documents/d1": { status: 200, body: DETAIL },
    });
    const opener = await screen.findByRole("button", { name: "Visualizar ata.pdf" });

    await user.click(opener);
    await user.click(await screen.findByRole("button", { name: "Fechar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByTestId("search")).toHaveTextContent("");
    expect(opener).toHaveFocus();

    await user.click(opener);
    await screen.findByRole("dialog", { name: "ata.pdf" });
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByTestId("search").textContent).toBe("");
  });

  it("o link de um arquivo duplicado (?documento=) abre a janela do documento existente", async () => {
    renderPage(
      { [LIST]: { status: 200, body: [doc()] }, "GET /api/documents/d1": { status: 200, body: DETAIL } },
      "/processos/p1/documentos?documento=d1",
    );
    const dialog = await screen.findByRole("dialog", { name: "ata.pdf" });
    expect(await within(dialog).findByText("Texto da ata")).toBeInTheDocument();
  });

  it("um documento inexistente (404) no ?documento= não deixa janela aberta e limpa a URL", async () => {
    renderPage(
      { [LIST]: { status: 200, body: [doc()] }, "GET /api/documents/d9": { status: 404, body: { detail: "Documento não encontrado" } } },
      "/processos/p1/documentos?documento=d9",
    );
    await screen.findByText("ata.pdf", { selector: "td" });
    await waitFor(() => expect(screen.getByTestId("search").textContent).toBe(""));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("TELA-09: criar atividade a partir do documento", () => {
  it("abre o formulário com o documento vinculado e o vincula à atividade criada, na página escolhida", async () => {
    let listed = 0;
    const { calls, user } = renderPage({
      [LIST]: () => {
        listed += 1;
        return { status: 200, body: [doc({ suggested_category: "SEM_ITEM_DE_PONTUACAO", confidence: null })] };
      },
      "POST /api/processes/p1/activities": { status: 201, body: { id: "a9", title: "Certificado do curso", version: 1 } },
      "POST /api/activities/a9/evidences": { status: 201, body: { id: "e1" } },
    });
    expect(await screen.findByText(/Sem item de pontuação: nenhuma atividade/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Criar atividade deste documento" }));

    const section = screen.getByRole("region", { name: "Criar atividade a partir do documento" });
    expect(within(section).getByText("ata.pdf")).toBeInTheDocument();
    await user.clear(within(section).getByLabelText("Página do documento de origem"));
    await user.type(within(section).getByLabelText("Página do documento de origem"), "2");
    await user.type(within(section).getByLabelText("Título"), "Certificado do curso");
    await user.click(within(section).getByRole("button", { name: "Salvar atividade" }));

    expect(await screen.findByRole("status")).toHaveTextContent("criada e vinculada a ata.pdf, página 2");
    const link = calls.find((c) => c.path === "/api/activities/a9/evidences")!;
    expect(JSON.parse(link.init?.body as string)).toEqual({ document_id: "d1", page: 2 });
    expect(listed).toBeGreaterThanOrEqual(2);
    expect(screen.queryByRole("region", { name: "Criar atividade a partir do documento" })).not.toBeInTheDocument();
  });

  it("EXTRAIDO_SEM_IA orienta o cadastro manual e oferece a criação da atividade", async () => {
    renderPage({ [LIST]: { status: 200, body: [doc({ status: "EXTRAIDO_SEM_IA", status_code: "IA_INDISPONIVEL", suggested_category: null })] } });
    expect(await screen.findByText(/A IA ficou indisponível/)).toHaveTextContent("cadastre a atividade manualmente");
    expect(screen.getByRole("button", { name: "Criar atividade deste documento" })).toBeInTheDocument();
  });
});
