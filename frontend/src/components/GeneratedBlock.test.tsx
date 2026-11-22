import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { DocumentKind, GeneratedDocument } from "../api/generated";
import { mockFetch } from "../test/fetchMock";
import { generated } from "../test/generatedFixtures";
import { GeneratedBlock } from "./GeneratedBlock";

const LIST = (kind: DocumentKind) => `GET /api/processes/p1/generated-documents?kind=${kind}`;
const ASK = "POST /api/processes/p1/generated-documents";

afterEach(() => {
  vi.useRealTimers();
});

type Props = Partial<Parameters<typeof GeneratedBlock>[0]>;

function setup(rows: GeneratedDocument[], extra: Parameters<typeof mockFetch>[0] = {}, props: Props = {}, kind: DocumentKind = "TABELA") {
  setCsrfToken("tok");
  const state = { rows };
  const mock = mockFetch({ [LIST(kind)]: () => ({ status: 200, body: state.rows }), ...extra });
  render(<GeneratedBlock processId="p1" kind={kind} {...props} />);
  return { ...mock, state, user: userEvent.setup() };
}

const asks = (calls: { method: string; path: string; init?: RequestInit }[]) => calls.filter((c) => `${c.method} ${c.path}` === ASK);

describe("UIG-01: um bloco por tipo, com botão, estado e histórico", () => {
  it("sem versões mostra o título do documento, o botão Gerar e que não há versão", async () => {
    setup([]);
    const block = await screen.findByRole("region", { name: "Tabela de Pontuação" });
    expect(within(block).getByRole("button", { name: "Gerar Tabela de Pontuação" })).toBeEnabled();
    expect(within(block).getByText("Nenhuma versão gerada ainda.")).toBeInTheDocument();
  });

  it("gerar pede o tipo, mostra GERANDO e desliga o botão", async () => {
    const { state, calls, user } = setup([], {
      [ASK]: () => {
        state.rows = [generated({ state: "GERANDO", version_number: null, files: [], finished_at: null })];
        return { status: 202, body: state.rows[0] };
      },
    });
    await user.click(await screen.findByRole("button", { name: "Gerar Tabela de Pontuação" }));
    expect(await screen.findByText("Gerando…")).toBeInTheDocument();
    expect(JSON.parse(String(asks(calls)[0].init?.body))).toEqual({ kind: "TABELA" });
    expect(screen.getByRole("button", { name: "Gerar Tabela de Pontuação" })).toBeDisabled();
  });

  it("consulta a cada 3 s até PRONTO e então mostra os links de cada formato com o tamanho", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { state, calls } = setup([generated({ state: "GERANDO", version_number: null, files: [], finished_at: null })]);
    expect(await screen.findByText("Gerando…")).toBeInTheDocument();
    const lists = () => calls.filter((c) => `${c.method} ${c.path}` === LIST("TABELA")).length;
    expect(lists()).toBe(1);

    state.rows = [generated()];
    await act(() => vi.advanceTimersByTimeAsync(3000));
    expect(lists()).toBe(2);
    const docx = await screen.findByRole("link", { name: "Baixar Tabela de Pontuação versão 1 em DOCX" });
    const pdf = screen.getByRole("link", { name: "Baixar Tabela de Pontuação versão 1 em PDF" });
    expect(docx).toHaveAttribute("href", "/api/generated-documents/g1/files/docx");
    expect(docx).toHaveTextContent("DOCX (40 KB)");
    expect(pdf).toHaveAttribute("href", "/api/generated-documents/g1/files/pdf");
    expect(pdf).toHaveTextContent("PDF (60 KB)");
    expect(screen.queryByText("Gerando…")).not.toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(lists()).toBe(2);
  });

  it("o histórico lista cada versão pronta, da mais nova para a mais antiga, com os tamanhos", async () => {
    setup([
      generated({ id: "g2", version_number: 2, files: [{ format: "PDF", size_bytes: 3_145_728, sha256: "c".repeat(64) }] }),
      generated({ id: "g1", version_number: 1 }),
    ]);
    const history = await screen.findByRole("list", { name: "Versões geradas" });
    const items = within(history).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Versão 2");
    expect(items[0]).toHaveTextContent("PDF (3,0 MB)");
    expect(items[1]).toHaveTextContent("Versão 1");
    expect(items[1]).toHaveTextContent("DOCX (40 KB)");
  });

  it("o Comprovante tem só o PDF", async () => {
    setup([generated({ kind: "COMPROVANTE", files: [{ format: "PDF", size_bytes: 52_428_800, sha256: "d".repeat(64) }] })], {}, {}, "COMPROVANTE");
    expect(await screen.findByRole("link", { name: "Baixar Comprovante de Documentos versão 1 em PDF" })).toHaveTextContent("PDF (50,0 MB)");
    expect(screen.queryByRole("link", { name: /DOCX/ })).not.toBeInTheDocument();
  });
});

describe("UIG-05: falha e alertas em português", () => {
  it("FALHOU mostra o motivo em português e permite tentar de novo", async () => {
    const { state, calls, user } = setup(
      [generated({ state: "FALHOU", version_number: null, files: [], error_code: "ORIGINAL_INDISPONIVEL", error_message: "Documento 2, página 3" })],
      {
        [ASK]: () => {
          state.rows = [generated({ id: "g2", state: "GERANDO", version_number: null, files: [] })];
          return { status: 202, body: state.rows[0] };
        },
      },
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("A geração falhou: Um documento de origem não está mais disponível ou a página não existe mais.");
    await user.click(screen.getByRole("button", { name: "Tentar de novo gerar Tabela de Pontuação" }));
    expect(await screen.findByText("Gerando…")).toBeInTheDocument();
    expect(asks(calls)).toHaveLength(1);
  });

  it("UIG-01: o histórico só lista versões PRONTO; a que falhou ou está gerando não entra", async () => {
    setup([
      generated({ id: "g3", state: "GERANDO", version_number: null, files: [], finished_at: null }),
      generated({ id: "g2", state: "FALHOU", version_number: null, files: [], error_code: "ERRO_INTERNO" }),
      generated({ id: "g1" }),
    ]);
    const history = await screen.findByRole("list", { name: "Versões geradas" });
    const items = within(history).getAllByRole("listitem");
    expect(items).toHaveLength(1);
    expect(items[0]).toHaveTextContent("Versão 1");
    expect(history).not.toHaveTextContent("Versão null");
  });

  it("lista os alertas da última versão pronta com o texto em português", async () => {
    setup([
      generated({
        alerts: [
          { code: "ATIVIDADE_SEM_COMPROVANTE", message: "Algoritmos" },
          { code: "PAGINA_RASTERIZADA", message: "Documento 1, página 2" },
        ],
      }),
    ]);
    const alerts = await screen.findByRole("list", { name: "Alertas da geração" });
    const items = within(alerts).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("Atividade sem comprovante anexado");
    expect(items[1]).toHaveTextContent("Página convertida em imagem para manter o que se vê");
  });

  it("o alerta de atividades fora do documento diz o rótulo uma vez, seguido das contagens", async () => {
    setup([
      generated({
        alerts: [{ code: "ATIVIDADES_FORA_DO_DOCUMENTO", message: "Atividades fora do documento: 1 sem enquadramento." }],
      }),
    ]);
    const alerts = await screen.findByRole("list", { name: "Alertas da geração" });
    expect(within(alerts).getByRole("listitem")).toHaveTextContent(
      /^Há atividades que ficaram fora do documento: 1 sem enquadramento\.$/,
    );
  });

  it("uma recusa 422 mostra a mensagem do servidor", async () => {
    const { user } = setup([], {
      [ASK]: { status: 422, body: { detail: [{ field: "geracao", code: "SEM_ATIVIDADES_VALIDADAS", message: "Nenhuma atividade validada." }] } },
    });
    await user.click(await screen.findByRole("button", { name: "Gerar Tabela de Pontuação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nenhuma atividade validada.");
  });

  it("409 GERACAO_EM_ANDAMENTO mostra a mensagem em português e relê a lista", async () => {
    const { calls, user } = setup([], {
      [ASK]: { status: 409, body: { detail: "em andamento", code: "GERACAO_EM_ANDAMENTO" } },
    });
    await user.click(await screen.findByRole("button", { name: "Gerar Tabela de Pontuação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Já há uma geração deste documento em andamento.");
    await waitFor(() => expect(calls.filter((c) => `${c.method} ${c.path}` === LIST("TABELA")).length).toBe(2));
  });
});

describe("UIG-06: aviso das atividades que ficam de fora", () => {
  it("mostra quantas atividades ficam de fora antes do botão de gerar", async () => {
    setup([], {}, { leftOut: 2 });
    const warning = await screen.findByText("2 atividades ficam de fora: só entram as validadas, com grupo e item.");
    const button = screen.getByRole("button", { name: "Gerar Tabela de Pontuação" });
    expect(warning.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("uma atividade fica no singular e nenhuma não mostra aviso", async () => {
    setup([], {}, { leftOut: 1 });
    expect(await screen.findByText("1 atividade fica de fora: só entram as validadas, com grupo e item.")).toBeInTheDocument();
  });

  it("sem atividade de fora não há aviso", async () => {
    setup([], {}, { leftOut: 0 });
    await screen.findByRole("button", { name: "Gerar Tabela de Pontuação" });
    expect(screen.queryByText(/ficam? de fora/)).not.toBeInTheDocument();
  });
});

describe("DEL-11: geração que o processo não aceita", () => {
  it("com um motivo para desligar, o botão fica desligado e o motivo aparece", async () => {
    setup([], {}, { disabledReason: "Os documentos de entrada foram excluídos: o Comprovante não pode mais ser gerado." }, "COMPROVANTE");
    const button = await screen.findByRole("button", { name: "Gerar Comprovante de Documentos" });
    expect(button).toBeDisabled();
    expect(screen.getByText(/Os documentos de entrada foram excluídos/)).toBeInTheDocument();
  });
});

describe("DOS-02: onReady avisa a página quando uma versão chega a PRONTO", () => {
  it("é chamado uma vez quando a versão em geração fica PRONTO, e não antes", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onReady = vi.fn();
    const { state } = setup([generated({ state: "GERANDO", version_number: null, files: [], finished_at: null })], {}, { onReady });
    expect(await screen.findByText("Gerando…")).toBeInTheDocument();
    expect(onReady).not.toHaveBeenCalled();

    state.rows = [generated()];
    await act(() => vi.advanceTimersByTimeAsync(3000));
    await screen.findByRole("link", { name: "Baixar Tabela de Pontuação versão 1 em DOCX" });
    expect(onReady).toHaveBeenCalledTimes(1);

    await act(() => vi.advanceTimersByTimeAsync(9000));
    expect(onReady).toHaveBeenCalledTimes(1);
  });

  it("uma versão que já estava PRONTO ao abrir o bloco não chama onReady", async () => {
    const onReady = vi.fn();
    setup([generated()], {}, { onReady });
    await screen.findByRole("link", { name: "Baixar Tabela de Pontuação versão 1 em DOCX" });
    expect(onReady).not.toHaveBeenCalled();
  });

  it("uma geração que falha não chama onReady", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onReady = vi.fn();
    const { state } = setup([generated({ state: "GERANDO", version_number: null, files: [], finished_at: null })], {}, { onReady });
    await screen.findByText("Gerando…");
    state.rows = [generated({ state: "FALHOU", version_number: null, files: [], error_code: "ERRO_INTERNO" })];
    await act(() => vi.advanceTimersByTimeAsync(3000));
    await screen.findByRole("alert");
    expect(onReady).not.toHaveBeenCalled();
  });
});
