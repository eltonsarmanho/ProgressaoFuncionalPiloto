import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ChecklistItem, ChecklistState } from "../api/board";
import { setCsrfToken } from "../api/client";
import { mockFetch } from "../test/fetchMock";
import { DossierChecklist } from "./DossierChecklist";

const GET = "GET /api/processes/p1/dossier";
const LATTES = "PUT /api/processes/p1/dossier/items/CURRICULO_LATTES";
const READ_ONLY_REASON = "O processo está concluído ou arquivado e não aceita alterações.";

type Row = [key: string, title: string, source: ChecklistItem["source"]];
const ROWS: Row[] = [
  ["REQUERIMENTO", "Requerimento", "GERADO"],
  ["PORTARIA_ULTIMA_PROGRESSAO", "Portaria da última progressão", "MANUAL"],
  ["DECLARACAO_PAGAMENTO", "Declaração de pagamento de exercícios anteriores", "MANUAL"],
  ["RELATORIO", "Relatório de Atividades", "GERADO"],
  ["TABELA", "Tabela de Pontuação", "GERADO"],
  ["COMPROVANTE", "Comprovante de Documentos", "GERADO"],
  ["CURRICULO_LATTES", "Currículo Lattes", "MANUAL"],
  ["PORTARIA_BANCA", "Portaria da banca", "PORTARIA_BANCA"],
  ["PARECER", "Parecer da banca", "GERADO"],
];

/** The nine items of the dossier; `over` changes one item by key. */
function checklist(over: Record<string, Partial<ChecklistItem>> = {}): ChecklistItem[] {
  return ROWS.map(([key, title, source], i) => ({
    key,
    order: i + 1,
    title,
    source,
    state: "PENDENTE" as ChecklistState,
    version_number: null,
    generation_id: null,
    outdated_table: false,
    ...over[key],
  }));
}

/** The spec's independent test: only Tabela, Relatório and Comprovante generated. */
const THREE_GENERATED = {
  RELATORIO: { state: "GERADO", version_number: 2, generation_id: "g-rel" },
  TABELA: { state: "GERADO", version_number: 2, generation_id: "g-tab" },
  COMPROVANTE: { state: "GERADO", version_number: 1, generation_id: "g-comp" },
} satisfies Record<string, Partial<ChecklistItem>>;

type Props = Partial<Parameters<typeof DossierChecklist>[0]>;

function setup(items: ChecklistItem[] | null = checklist(THREE_GENERATED), extra: Parameters<typeof mockFetch>[0] = {}, props: Props = {}) {
  setCsrfToken("tok");
  const mock = mockFetch({
    [GET]: items ? { status: 200, body: items } : { status: 404, body: { detail: "Não encontrado" } },
    ...extra,
  });
  render(<DossierChecklist processId="p1" {...props} />);
  return { ...mock, user: userEvent.setup() };
}

const list = () => screen.findByRole("list", { name: "Ordem de entrega do dossiê" });
const rowOf = async (title: string) => {
  const items = within(await list()).getAllByRole("listitem");
  const found = items.find((li) => within(li).queryByText(title) !== null);
  if (!found) throw new Error(`no item for ${title}`);
  return found;
};

describe("DOS-01, ORD-01: a lista na ordem recebida da API", () => {
  it("mostra os nove itens na ordem recebida, com o número de cada um", async () => {
    setup();
    const items = within(await list()).getAllByRole("listitem");
    expect(items.map((li) => li.getAttribute("value"))).toEqual(["1", "2", "3", "4", "5", "6", "7", "8", "9"]);
    expect(items[0]).toHaveTextContent("Requerimento");
    expect(items[8]).toHaveTextContent("Parecer da banca");
  });

  it("não reordena: a ordem é a do arquivo de configuração do servidor", async () => {
    const all = checklist();
    setup([all[4], all[0], all[3]]);
    const items = within(await list()).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      expect.stringContaining("Tabela de Pontuação"),
      expect.stringContaining("Requerimento"),
      expect.stringContaining("Relatório de Atividades"),
    ]);
  });

  it("um erro ao ler a lista mostra a mensagem em vez da lista", async () => {
    setup(null);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não encontrado");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});

describe("DOS-02, DOS-05: Gerado com a versão e o link, e Pendente", () => {
  it("três itens Gerado com o número da última versão e o link de download, e seis Pendente", async () => {
    setup();
    const items = within(await list()).getAllByRole("listitem");
    const states = items.map((li) => within(li).getByTestId("checklist-state").textContent);
    expect(states).toEqual(["Pendente", "Pendente", "Pendente", "Gerado", "Gerado", "Gerado", "Pendente", "Pendente", "Pendente"]);
    const table = await rowOf("Tabela de Pontuação");
    expect(within(table).getByText("versão 2")).toBeInTheDocument();
    expect(within(table).getByRole("link", { name: "Baixar Tabela de Pontuação versão 2 em PDF" })).toHaveAttribute(
      "href",
      "/api/generated-documents/g-tab/files/pdf",
    );
    expect(within(table).getByRole("link", { name: "Baixar Tabela de Pontuação versão 2 em DOCX" })).toHaveAttribute(
      "href",
      "/api/generated-documents/g-tab/files/docx",
    );
    const proof = await rowOf("Comprovante de Documentos");
    expect(within(proof).getByText("versão 1")).toBeInTheDocument();
  });

  it("um item pendente não tem versão nem link", async () => {
    setup();
    const requirement = await rowOf("Requerimento");
    expect(within(requirement).queryByText(/versão/)).not.toBeInTheDocument();
    expect(within(requirement).queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("DOS-03: Portaria da banca registrada", () => {
  it("mostra a Portaria da banca como Registrada, sem caixa Entregue nem link", async () => {
    setup(checklist({ PORTARIA_BANCA: { state: "REGISTRADA" } }));
    const board = await rowOf("Portaria da banca");
    expect(within(board).getByTestId("checklist-state")).toHaveTextContent("Registrada");
    expect(within(board).queryByRole("checkbox")).not.toBeInTheDocument();
    expect(within(board).queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("DOS-04: marcar e desmarcar Entregue", () => {
  it("só os itens que o sistema não produz têm a caixa Entregue", async () => {
    setup();
    const boxes = (await screen.findAllByRole("checkbox")).map((box) => box.getAttribute("aria-label"));
    expect(boxes).toEqual([
      "Entregue: Portaria da última progressão",
      "Entregue: Declaração de pagamento de exercícios anteriores",
      "Entregue: Currículo Lattes",
    ]);
  });

  it("marcar 'Currículo Lattes' envia entregue true, sem justificativa, e a lista nova mostra Entregue", async () => {
    const { calls, user } = setup(checklist(THREE_GENERATED), {
      [LATTES]: { status: 200, body: checklist({ ...THREE_GENERATED, CURRICULO_LATTES: { state: "ENTREGUE" } }) },
    });
    await user.click(await screen.findByRole("checkbox", { name: "Entregue: Currículo Lattes" }));
    await waitFor(() => expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1));
    expect(JSON.parse(String(calls.find((c) => c.method === "PUT")!.init?.body))).toEqual({ entregue: true });
    const lattes = await rowOf("Currículo Lattes");
    await waitFor(() => expect(within(lattes).getByTestId("checklist-state")).toHaveTextContent("Entregue"));
    expect(within(lattes).getByRole("checkbox")).toBeChecked();
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
  });

  it("desmarcar um item entregue envia entregue false e a lista volta a Pendente", async () => {
    const { calls, user } = setup(checklist({ ...THREE_GENERATED, CURRICULO_LATTES: { state: "ENTREGUE" } }), {
      [LATTES]: { status: 200, body: checklist(THREE_GENERATED) },
    });
    const box = await screen.findByRole("checkbox", { name: "Entregue: Currículo Lattes" });
    expect(box).toBeChecked();
    await user.click(box);
    await waitFor(() => expect(calls.filter((c) => c.method === "PUT")).toHaveLength(1));
    expect(JSON.parse(String(calls.find((c) => c.method === "PUT")!.init?.body))).toEqual({ entregue: false });
    const lattes = await rowOf("Currículo Lattes");
    await waitFor(() => expect(within(lattes).getByTestId("checklist-state")).toHaveTextContent("Pendente"));
    expect(within(lattes).getByRole("checkbox")).not.toBeChecked();
  });

  it("um erro de gravação aparece em um alerta e a marca não muda", async () => {
    const { user } = setup(checklist(THREE_GENERATED), {
      [LATTES]: { status: 409, body: { detail: "x", code: "PROCESSO_SOMENTE_LEITURA" } },
    });
    const box = await screen.findByRole("checkbox", { name: "Entregue: Currículo Lattes" });
    await user.click(box);
    expect(await screen.findByRole("alert")).toHaveTextContent(READ_ONLY_REASON);
    expect(box).not.toBeChecked();
  });
});

describe("DOS-06: a Tabela gerada com outra versão da tabela de pontuação", () => {
  it("o aviso aparece só no item da Tabela", async () => {
    setup(checklist({ ...THREE_GENERATED, TABELA: { ...THREE_GENERATED.TABELA, outdated_table: true } }));
    const table = await rowOf("Tabela de Pontuação");
    expect(within(table).getByText("Gerada com outra versão da tabela de pontuação; gere de novo")).toBeInTheDocument();
    expect(screen.getAllByText("Gerada com outra versão da tabela de pontuação; gere de novo")).toHaveLength(1);
  });

  it("sem a marca outdated_table nenhum aviso aparece", async () => {
    setup();
    await list();
    expect(screen.queryByText(/Gerada com outra versão/)).not.toBeInTheDocument();
  });
});

describe("BNAV-02: somente leitura", () => {
  it("desabilita as caixas com o motivo e não envia nada", async () => {
    const { calls, user } = setup(checklist(THREE_GENERATED), {}, { readOnly: true, readOnlyReason: READ_ONLY_REASON });
    const boxes = await screen.findAllByRole("checkbox");
    expect(boxes).toHaveLength(3);
    for (const box of boxes) expect(box).toBeDisabled();
    expect(screen.getByText(READ_ONLY_REASON)).toBeInTheDocument();
    await user.click(boxes[2]);
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
  });

  it("mantém o link de download dos itens gerados", async () => {
    setup(checklist(THREE_GENERATED), {}, { readOnly: true, readOnlyReason: READ_ONLY_REASON });
    expect(await screen.findByRole("link", { name: "Baixar Relatório de Atividades versão 2 em PDF" })).toBeInTheDocument();
  });
});

describe("a lista se atualiza quando a página pede", () => {
  it("lê de novo quando refreshKey muda (um documento chegou a PRONTO)", async () => {
    setCsrfToken("tok");
    let ready = false;
    const { calls } = mockFetch({
      [GET]: () => ({
        status: 200,
        body: checklist(ready ? { REQUERIMENTO: { state: "GERADO", version_number: 1, generation_id: "g-req" } } : {}),
      }),
    });
    const { rerender } = render(<DossierChecklist processId="p1" refreshKey={0} />);
    expect(within(await rowOf("Requerimento")).getByTestId("checklist-state")).toHaveTextContent("Pendente");
    ready = true;
    rerender(<DossierChecklist processId="p1" refreshKey={1} />);
    await waitFor(async () => expect(within(await rowOf("Requerimento")).getByTestId("checklist-state")).toHaveTextContent("Gerado"));
    expect(calls.filter((c) => c.method === "GET")).toHaveLength(2);
  });
});
