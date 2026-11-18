import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";
import { setCsrfToken } from "../api/client";
import type { DocumentKind } from "../api/generated";
import type { Activity, Process, ProcessStatus } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { DOCUMENTS, draftView, generated, layoutView, preview } from "../test/generatedFixtures";
import { ProcessGenerated } from "./ProcessGenerated";

function process(status: ProcessStatus, version = 7): Process {
  return { id: "p1", status, version } as Process;
}

function activity(id: string, status: Activity["status"], group: number | null, item: number | null): Activity {
  return { id, process_id: "p1", title: id, status, group_number: group, item_number: item } as Activity;
}

/** Four activities: 1 enters, 1 is pending, 1 is validated without an item, 1 was rejected. */
const ACTIVITIES = [
  activity("ok", "VALIDADA", 1, 1),
  activity("pendente", "AGUARDANDO_REVISAO", 1, 1),
  activity("sem-item", "VALIDADA", null, null),
  activity("rejeitada", "REJEITADA", 2, 1),
];

const DOSSIER = [
  { order: 1, title: "Requerimento à CPPD", generated_by: null },
  { order: 2, title: "Relatório de Atividades", generated_by: "RELATORIO" },
];

type Rows = Partial<Record<DocumentKind, ReturnType<typeof generated>[]>>;

function setup(status: ProcessStatus, rows: Rows = {}, extra: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const state = { status };
  const mock = mockFetch({
    "GET /api/processes/p1": () => ({ status: 200, body: process(state.status) }),
    "GET /api/processes/p1/activities": { status: 200, body: ACTIVITIES },
    "GET /api/processes/p1/generated-documents?kind=TABELA": { status: 200, body: rows.TABELA ?? [] },
    "GET /api/processes/p1/generated-documents?kind=RELATORIO": { status: 200, body: rows.RELATORIO ?? [] },
    "GET /api/processes/p1/generated-documents?kind=COMPROVANTE": { status: 200, body: rows.COMPROVANTE ?? [] },
    "GET /api/processes/p1/report-draft": { status: 200, body: draftView() },
    "GET /api/processes/p1/report-draft/wording": { status: 200, body: [] },
    "GET /api/processes/p1/comprovante-layout": { status: 200, body: layoutView() },
    "GET /api/processes/p1/documents": { status: 200, body: DOCUMENTS },
    "GET /api/dossier-order": { status: 200, body: DOSSIER },
    "GET /api/processes/p1/conclusion": { status: 200, body: preview() },
    ...extra,
  });
  render(
    <MemoryRouter initialEntries={["/processos/p1/gerados"]}>
      <Routes>
        <Route path="processos/:id/gerados" element={<ProcessGenerated />} />
      </Routes>
    </MemoryRouter>,
  );
  return { ...mock, state, user: userEvent.setup() };
}

const block = (name: string) => screen.findByRole("region", { name });

describe("UIG-01: a página da Etapa 5", () => {
  it("mostra a navegação com a Etapa 5 atual, os três blocos e a ordem do dossiê", async () => {
    setup("EM_ANDAMENTO");
    expect(screen.getByRole("heading", { name: "Etapa 5 · Documentos gerados" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getAllByRole("listitem")[4]).toHaveAttribute("aria-current", "step");
    await block("Tabela de Pontuação");
    await block("Relatório de Atividades");
    await block("Comprovante de Documentos");
    const order = await screen.findByRole("list", { name: "Ordem de entrega do dossiê" });
    expect(within(order).getAllByRole("listitem")).toHaveLength(2);
  });

  it("UIG-06: cada bloco avisa quantas atividades ficam de fora (pendentes e sem item; a rejeitada não conta)", async () => {
    setup("EM_ANDAMENTO");
    for (const name of ["Tabela de Pontuação", "Relatório de Atividades", "Comprovante de Documentos"]) {
      const b = await block(name);
      expect(await within(b).findByText("2 atividades ficam de fora: só entram as validadas, com grupo e item.")).toBeInTheDocument();
    }
  });

  it("o histórico de cada bloco traz os links de download da versão pronta", async () => {
    setup("EM_ANDAMENTO", { TABELA: [generated()] });
    const b = await block("Tabela de Pontuação");
    expect(await within(b).findByRole("link", { name: "Baixar Tabela de Pontuação versão 1 em PDF" })).toHaveAttribute(
      "href",
      "/api/generated-documents/g1/files/pdf",
    );
  });
});

describe("UIG-02, UIG-03: o editor do Relatório e o arranjo do Comprovante", () => {
  it("abre o rascunho dentro do bloco do Relatório, com as seções", async () => {
    const { user } = setup("EM_ANDAMENTO");
    const b = await block("Relatório de Atividades");
    expect(within(b).queryByRole("region", { name: /1\.1 Ensino de graduação/ })).not.toBeInTheDocument();
    await user.click(within(b).getByRole("button", { name: "Revisar rascunho do Relatório" }));
    expect(await within(b).findByRole("region", { name: /1\.1 Ensino de graduação/ })).toBeInTheDocument();
    expect(within(b).getByRole("region", { name: /2 Pesquisa/ })).toBeInTheDocument();
    expect(within(b).getByRole("button", { name: "Pedir redação de 1.1" })).toBeInTheDocument();
  });

  it("abre o arranjo dentro do bloco do Comprovante, por grupo e atividade", async () => {
    const { user } = setup("EM_ANDAMENTO");
    const b = await block("Comprovante de Documentos");
    await user.click(within(b).getByRole("button", { name: "Revisar arranjo do Comprovante" }));
    expect(await within(b).findByRole("region", { name: /Grupo I/ })).toBeInTheDocument();
    expect(within(b).getByRole("listitem", { name: "Algoritmos" })).toBeInTheDocument();
    expect(within(b).getByRole("button", { name: "Salvar arranjo" })).toBeInTheDocument();
  });
});

describe("UIG-09: Concluir e excluir documentos de entrada", () => {
  it("só o processo EM_ANDAMENTO oferece o botão, que abre a confirmação", async () => {
    const { user } = setup("EM_ANDAMENTO");
    await block("Tabela de Pontuação");
    await user.click(await screen.findByRole("button", { name: "Concluir e excluir documentos de entrada" }));
    const dialog = await screen.findByRole("dialog", { name: "Concluir e excluir documentos de entrada" });
    expect(await within(dialog).findByText(/serão excluídos de forma irreversível/)).toBeInTheDocument();
  });

  it.each(["RASCUNHO", "ARQUIVADO"] as const)("o processo %s não oferece a conclusão", async (status) => {
    setup(status);
    await block("Tabela de Pontuação");
    expect(screen.queryByRole("button", { name: "Concluir e excluir documentos de entrada" })).not.toBeInTheDocument();
  });

  it("ao concluir, a página recarrega o processo: o botão some e o Comprovante deixa de ser gerado", async () => {
    const { state, user } = setup("EM_ANDAMENTO", {}, {
      "POST /api/processes/p1/conclusion": {
        status: 200,
        body: { status: "CONCLUIDO", arquivos_removidos: 3, arquivos_pendentes: 0, bytes_liberados: 5_242_880, alertas: [] },
      },
    });
    const comprovante = await block("Comprovante de Documentos");
    await waitFor(() =>
      expect(within(comprovante).getByRole("button", { name: "Gerar Comprovante de Documentos" })).toBeEnabled(),
    );
    await user.click(await screen.findByRole("button", { name: "Concluir e excluir documentos de entrada" }));
    const dialog = await screen.findByRole("dialog");
    state.status = "CONCLUIDO";
    await user.click(await within(dialog).findByLabelText(/Confirmo a exclusão irreversível/));
    await user.click(within(dialog).getByRole("button", { name: "Concluir e excluir" }));
    expect(await within(dialog).findByText("Processo concluído.")).toBeInTheDocument();
    await waitFor(() =>
      expect(within(screen.getByRole("region", { name: "Comprovante de Documentos" })).getByRole("button", { name: "Gerar Comprovante de Documentos" })).toBeDisabled(),
    );
    expect(screen.queryByRole("button", { name: "Concluir e excluir documentos de entrada" })).not.toBeInTheDocument();
  });
});

describe("DEL-13: processo CONCLUIDO", () => {
  const rows: Rows = {
    TABELA: [generated()],
    RELATORIO: [generated({ id: "g2", kind: "RELATORIO" })],
    COMPROVANTE: [generated({ id: "g3", kind: "COMPROVANTE", files: [{ format: "PDF", size_bytes: 9_437_184, sha256: "e".repeat(64) }] })],
  };

  it("Tabela e Relatório geram e todos os blocos baixam; o Comprovante fica desligado com ORIGINAIS_EXCLUIDOS", async () => {
    setup("CONCLUIDO", rows);
    const tabela = await block("Tabela de Pontuação");
    const relatorio = await block("Relatório de Atividades");
    const comprovante = await block("Comprovante de Documentos");
    await waitFor(() => expect(within(tabela).getByRole("button", { name: "Gerar Tabela de Pontuação" })).toBeEnabled());
    await waitFor(() => expect(within(relatorio).getByRole("button", { name: "Gerar Relatório de Atividades" })).toBeEnabled());
    const gerarComprovante = within(comprovante).getByRole("button", { name: "Gerar Comprovante de Documentos" });
    expect(gerarComprovante).toBeDisabled();
    expect(within(comprovante).getByText("Os documentos de entrada foram excluídos: o Comprovante não pode mais ser gerado.")).toBeInTheDocument();
    expect(await within(tabela).findByRole("link", { name: "Baixar Tabela de Pontuação versão 1 em DOCX" })).toBeInTheDocument();
    expect(await within(relatorio).findByRole("link", { name: "Baixar Relatório de Atividades versão 1 em PDF" })).toBeInTheDocument();
    expect(await within(comprovante).findByRole("link", { name: "Baixar Comprovante de Documentos versão 1 em PDF" })).toBeInTheDocument();
  });

  it("o rascunho e o arranjo ficam somente leitura", async () => {
    const { user } = setup("CONCLUIDO", rows);
    const relatorio = await block("Relatório de Atividades");
    await user.click(within(relatorio).getByRole("button", { name: "Revisar rascunho do Relatório" }));
    expect(await within(relatorio).findByLabelText("Texto de Algoritmos")).toHaveAttribute("readonly");
    expect(within(relatorio).queryByRole("button", { name: /Pedir redação/ })).not.toBeInTheDocument();
    expect(within(relatorio).queryByRole("combobox", { name: /Mover/ })).not.toBeInTheDocument();

    const comprovante = await block("Comprovante de Documentos");
    await user.click(within(comprovante).getByRole("button", { name: "Revisar arranjo do Comprovante" }));
    expect(await within(comprovante).findByRole("listitem", { name: "Algoritmos" })).toBeInTheDocument();
    expect(within(comprovante).queryByRole("button", { name: /Salvar arranjo|Subir|Descer|Remover|Acrescentar/ })).not.toBeInTheDocument();
  });
});
