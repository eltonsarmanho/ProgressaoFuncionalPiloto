import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { setCsrfToken } from "../api/client";
import type { LayoutView } from "../api/generated";
import { mockFetch } from "../test/fetchMock";
import { ACT_A, ACT_B, DOC_1, DOC_2, DOCUMENTS, layoutView } from "../test/generatedFixtures";
import { ComprovanteLayoutEditor } from "./ComprovanteLayoutEditor";

const GET = "GET /api/processes/p1/comprovante-layout";
const PUT = "PUT /api/processes/p1/comprovante-layout";
const DOCS = "GET /api/processes/p1/documents";

function setup(view: LayoutView = layoutView(), extra: Parameters<typeof mockFetch>[0] = {}, readOnly = false) {
  setCsrfToken("tok");
  const mock = mockFetch({
    [GET]: () => ({ status: 200, body: view }),
    [DOCS]: { status: 200, body: DOCUMENTS },
    ...extra,
  });
  render(<ComprovanteLayoutEditor processId="p1" readOnly={readOnly} />);
  return { ...mock, user: userEvent.setup() };
}

const putBody = (calls: { method: string; init?: RequestInit }[]) =>
  JSON.parse(String(calls.find((c) => c.method === "PUT")!.init?.body));

/** The layout after the user moved the second page of Algoritmos up and removed nothing else. */
function swapped(): LayoutView {
  const view = layoutView();
  view.layout = {
    ...view.layout,
    version: 4,
    activities: view.layout.activities.map((a) =>
      a.activity_id === ACT_A ? { ...a, pages: [...a.pages].reverse() } : a,
    ),
  };
  view.plan.toc = view.plan.toc.map((e) =>
    e.activity_id === ACT_A
      ? {
          ...e,
          sources: [
            { document_id: DOC_1, source_page: 5, comprovante_page: 4, remission: false, justification: null },
            { document_id: DOC_1, source_page: 2, comprovante_page: 5, remission: false, justification: null },
          ],
        }
      : e,
  );
  return view;
}

describe("UIG-03: arranjo por grupo, item e atividade", () => {
  it("mostra o grupo, a atividade, o documento de cada página e a numeração prevista do plano", async () => {
    setup();
    const group = await screen.findByRole("region", { name: /Grupo I/ });
    expect(within(group).getByText("Docência")).toBeInTheDocument();
    const algoritmos = within(group).getByRole("listitem", { name: "Algoritmos" });
    const pages = within(algoritmos).getAllByRole("listitem");
    expect(pages[0]).toHaveTextContent("certificado-a.pdf, página 2");
    expect(pages[0]).toHaveTextContent("Comprovante p. 4");
    expect(pages[1]).toHaveTextContent("certificado-a.pdf, página 5");
    expect(pages[1]).toHaveTextContent("Comprovante p. 5");
    expect(algoritmos).toHaveTextContent("pp. 4 a 5");
    expect(within(group).getByRole("listitem", { name: "Redes" })).toHaveTextContent("declaracao-b.pdf, página 1");
  });

  it("a atividade sem página mostra que não tem comprovante anexado", async () => {
    const view = layoutView();
    view.layout.activities[1] = { ...view.layout.activities[1], pages: [] };
    setup(view);
    const redes = await screen.findByRole("listitem", { name: "Redes" });
    expect(redes).toHaveTextContent("Sem comprovante anexado");
  });

  it("a página repetida mostra a remissão ao número em que ela está", async () => {
    const view = layoutView();
    view.plan.toc[2] = {
      ...view.plan.toc[2],
      sources: [{ document_id: DOC_2, source_page: 1, comprovante_page: 4, remission: true, justification: null }],
    };
    setup(view);
    const redes = await screen.findByRole("listitem", { name: "Redes" });
    expect(redes).toHaveTextContent("ver Comprovante p. 4");
  });
});

describe("ARR-04: reordenar e ARR-03: remover páginas", () => {
  it("subir a segunda página só muda a tela até salvar; salvar manda a ordem nova com a versão do servidor", async () => {
    const { calls, user } = setup(layoutView(), { [PUT]: { status: 200, body: swapped() } });
    await screen.findByRole("listitem", { name: "Algoritmos" });
    await user.click(screen.getByRole("button", { name: "Subir página 5 de certificado-a.pdf em Algoritmos" }));

    const algoritmos = screen.getByRole("listitem", { name: "Algoritmos" });
    expect(within(algoritmos).getAllByRole("listitem")[0]).toHaveTextContent("página 5");
    expect(calls.filter((c) => c.method === "PUT")).toHaveLength(0);
    expect(screen.getByText(/Alterações não salvas/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    await waitFor(() => expect(screen.queryByText(/Alterações não salvas/)).not.toBeInTheDocument());
    const body = putBody(calls);
    expect(body.expected_version).toBe(3);
    expect(body.activities[0].pages.map((p: { page: number }) => p.page)).toEqual([5, 2]);
    // the numbering is the one the server planned for the saved order
    const first = within(screen.getByRole("listitem", { name: "Algoritmos" })).getAllByRole("listitem")[0];
    expect(first).toHaveTextContent("página 5");
    expect(first).toHaveTextContent("Comprovante p. 4");
  });

  it("reordenar duas páginas e remover uma: salva a ordem nova sem a página removida, com todas as atividades", async () => {
    const saved = swapped();
    saved.layout.activities[1] = { ...saved.layout.activities[1], pages: [] };
    const { calls, user } = setup(layoutView(), { [PUT]: { status: 200, body: saved } });
    await screen.findByRole("listitem", { name: "Algoritmos" });
    await user.click(screen.getByRole("button", { name: "Descer página 2 de certificado-a.pdf em Algoritmos" }));
    await user.click(screen.getByRole("button", { name: "Remover página 1 de declaracao-b.pdf em Redes" }));
    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    const body = putBody(calls);
    expect(body.activities).toHaveLength(2);
    expect(body.activities[0].pages).toEqual([
      { document_id: DOC_1, page: 5, repeat_justification: null },
      { document_id: DOC_1, page: 2, repeat_justification: null },
    ]);
    expect(body.activities[1].pages).toEqual([]);
    expect(await screen.findByText("Sem comprovante anexado")).toBeInTheDocument();
  });

  it("a numeração prevista some enquanto há alterações não salvas e Descartar volta ao arranjo salvo", async () => {
    const { user } = setup();
    await screen.findByRole("listitem", { name: "Algoritmos" });
    await user.click(screen.getByRole("button", { name: "Remover página 5 de certificado-a.pdf em Algoritmos" }));
    expect(screen.queryByText(/Comprovante p\. 4/)).not.toBeInTheDocument();
    expect(screen.getByText(/numeração aparece depois de salvar/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Descartar alterações" }));
    const algoritmos = screen.getByRole("listitem", { name: "Algoritmos" });
    expect(within(algoritmos).getAllByRole("listitem")).toHaveLength(2);
    expect(algoritmos).toHaveTextContent("Comprovante p. 4");
  });

  it("os botões de ordem são botões do teclado e os das pontas ficam desligados, sem arrastar e soltar", async () => {
    const { user } = setup();
    await screen.findByRole("listitem", { name: "Algoritmos" });
    expect(screen.getByRole("button", { name: "Subir página 2 de certificado-a.pdf em Algoritmos" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Descer página 5 de certificado-a.pdf em Algoritmos" })).toBeDisabled();
    expect(document.querySelector("[draggable]")).toBeNull();

    screen.getByRole("button", { name: "Descer página 2 de certificado-a.pdf em Algoritmos" }).focus();
    await user.keyboard("{Enter}");
    const pages = within(screen.getByRole("listitem", { name: "Algoritmos" })).getAllByRole("listitem");
    expect(pages[0]).toHaveTextContent("página 5");
  });

  it("subir e descer a atividade dentro do item muda a ordem enviada", async () => {
    const { calls, user } = setup(layoutView(), { [PUT]: { status: 200, body: layoutView() } });
    await screen.findByRole("listitem", { name: "Algoritmos" });
    await user.click(screen.getByRole("button", { name: "Descer atividade Algoritmos" }));
    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(putBody(calls).activities.map((a: { activity_id: string }) => a.activity_id)).toEqual([ACT_B, ACT_A]);
  });

  it("ARR-05: a atividade não muda de item; o corpo leva o grupo e o item que o servidor deu", async () => {
    const { calls, user } = setup(layoutView(), { [PUT]: { status: 200, body: layoutView() } });
    await screen.findByRole("listitem", { name: "Algoritmos" });
    expect(screen.queryByRole("combobox", { name: /item/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Descer página 2 de certificado-a.pdf em Algoritmos" }));
    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    for (const activity of putBody(calls).activities) {
      expect([activity.group_number, activity.item_number]).toEqual([1, 1]);
    }
  });
});

describe("ARR-07: 409 recarrega e avisa", () => {
  it("recarrega o arranjo do servidor, descarta a edição local e mostra o aviso em português", async () => {
    let reads = 0;
    const { calls, user } = setup(layoutView(), {
      [GET]: () => ({ status: 200, body: reads++ === 0 ? layoutView() : swapped() }),
      [PUT]: { status: 409, body: { detail: "Versão desatualizada", code: "VERSAO_DESATUALIZADA" } },
    });
    await screen.findByRole("listitem", { name: "Algoritmos" });
    await user.click(screen.getByRole("button", { name: "Remover página 5 de certificado-a.pdf em Algoritmos" }));
    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Os dados mudaram desde que você abriu a tela");
    await waitFor(() => expect(calls.filter((c) => `${c.method} ${c.path}` === GET)).toHaveLength(2));
    const pages = within(await screen.findByRole("listitem", { name: "Algoritmos" })).getAllByRole("listitem");
    expect(pages).toHaveLength(2);
    expect(pages[0]).toHaveTextContent("página 5");
    expect(screen.queryByText(/Alterações não salvas/)).not.toBeInTheDocument();
  });
});

describe("DEL-13: somente leitura", () => {
  it("em processo concluído mostra o arranjo sem botões de edição", async () => {
    setup(layoutView(), {}, true);
    await screen.findByRole("listitem", { name: "Algoritmos" });
    expect(screen.queryByRole("button", { name: /Subir|Descer|Remover|Salvar/ })).not.toBeInTheDocument();
  });
});

describe("ARR-02: acrescentar página", () => {
  async function openForm(user: ReturnType<typeof userEvent.setup>, activity = "Algoritmos") {
    await screen.findByRole("listitem", { name: activity });
    await user.click(screen.getByRole("button", { name: `Acrescentar página em ${activity}` }));
    return screen.getByRole("group", { name: `Acrescentar página em ${activity}` });
  }

  it("oferece só os documentos do processo e grava a página na posição pedida", async () => {
    const { calls, user } = setup(layoutView(), { [PUT]: { status: 200, body: layoutView() } });
    const form = await openForm(user);
    const options = within(within(form).getByLabelText("Documento")).getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Escolha o documento", "certificado-a.pdf (8 páginas)", "declaracao-b.pdf (3 páginas)"]);
    await user.selectOptions(within(form).getByLabelText("Documento"), DOC_2);
    await user.clear(within(form).getByLabelText("Página"));
    await user.type(within(form).getByLabelText("Página"), "3");
    await user.clear(within(form).getByLabelText("Posição"));
    await user.type(within(form).getByLabelText("Posição"), "2");
    await user.click(within(form).getByRole("button", { name: "Acrescentar" }));

    const pages = within(screen.getByRole("listitem", { name: "Algoritmos" })).getAllByRole("listitem");
    expect(pages.map((p) => p.textContent)).toEqual([
      expect.stringContaining("certificado-a.pdf, página 2"),
      expect.stringContaining("declaracao-b.pdf, página 3"),
      expect.stringContaining("certificado-a.pdf, página 5"),
    ]);
    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(putBody(calls).activities[0].pages.map((p: { document_id: string; page: number }) => [p.document_id, p.page])).toEqual([
      [DOC_1, 2],
      [DOC_2, 3],
      [DOC_1, 5],
    ]);
  });

  it("sem posição a página vai para o fim da atividade", async () => {
    const { user } = setup();
    const form = await openForm(user, "Redes");
    await user.selectOptions(within(form).getByLabelText("Documento"), DOC_1);
    await user.clear(within(form).getByLabelText("Página"));
    await user.type(within(form).getByLabelText("Página"), "7");
    await user.click(within(form).getByRole("button", { name: "Acrescentar" }));
    const pages = within(screen.getByRole("listitem", { name: "Redes" })).getAllByRole("listitem");
    expect(pages[pages.length - 1]).toHaveTextContent("certificado-a.pdf, página 7");
  });

  it("página fora do documento mostra o erro e não acrescenta nada", async () => {
    const { user } = setup();
    const form = await openForm(user);
    await user.selectOptions(within(form).getByLabelText("Documento"), DOC_2);
    await user.clear(within(form).getByLabelText("Página"));
    await user.type(within(form).getByLabelText("Página"), "4");
    await user.click(within(form).getByRole("button", { name: "Acrescentar" }));
    expect(within(form).getByRole("alert")).toHaveTextContent("A página indicada não existe no documento.");
    expect(within(screen.getByRole("listitem", { name: "Algoritmos" })).getAllByRole("listitem")).toHaveLength(2);
  });

  it("o 422 PAGINA_FORA_DO_DOCUMENTO do servidor ao salvar mostra a mensagem do erro", async () => {
    const { user } = setup(layoutView(), {
      [PUT]: {
        status: 422,
        body: { detail: [{ field: "geracao", code: "PAGINA_FORA_DO_DOCUMENTO", message: "A página 9 não existe no documento declaracao-b.pdf." }] },
      },
    });
    const form = await openForm(user);
    await user.selectOptions(within(form).getByLabelText("Documento"), DOC_1);
    await user.clear(within(form).getByLabelText("Página"));
    await user.type(within(form).getByLabelText("Página"), "7");
    await user.click(within(form).getByRole("button", { name: "Acrescentar" }));
    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A página 9 não existe no documento declaracao-b.pdf.");
    expect(screen.getByText(/Alterações não salvas/)).toBeInTheDocument();
  });
});

describe("CMP-06: repetir a página com justificativa", () => {
  /** Redes gets page 2 of certificado-a.pdf, which Algoritmos already has: it is a remission. */
  async function addShared(user: ReturnType<typeof userEvent.setup>) {
    await screen.findByRole("listitem", { name: "Redes" });
    await user.click(screen.getByRole("button", { name: "Acrescentar página em Redes" }));
    const form = screen.getByRole("group", { name: "Acrescentar página em Redes" });
    await user.selectOptions(within(form).getByLabelText("Documento"), DOC_1);
    await user.clear(within(form).getByLabelText("Página"));
    await user.type(within(form).getByLabelText("Página"), "2");
    await user.click(within(form).getByRole("button", { name: "Acrescentar" }));
  }

  it("a página que outra atividade já tem oferece repetir; sem justificativa não repete", async () => {
    const { user } = setup();
    await addShared(user);
    await user.click(screen.getByRole("button", { name: "Repetir página 2 de certificado-a.pdf em Redes com justificativa" }));
    const dialog = screen.getByRole("dialog", { name: "Repetir página" });
    await user.click(within(dialog).getByRole("button", { name: "Repetir página" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Informe a justificativa da repetição.");
    expect(screen.queryByText(/Repetida:/)).not.toBeInTheDocument();
  });

  it("com a justificativa a página é anexada de novo e o corpo leva repeat_justification", async () => {
    const { calls, user } = setup(layoutView(), { [PUT]: { status: 200, body: layoutView() } });
    await addShared(user);
    await user.click(screen.getByRole("button", { name: "Repetir página 2 de certificado-a.pdf em Redes com justificativa" }));
    await user.type(screen.getByLabelText("Justificativa da repetição"), "O mesmo certificado comprova as duas atividades");
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Repetir página" }));
    expect(screen.getByText(/Repetida: O mesmo certificado comprova as duas atividades/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Salvar arranjo" }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(putBody(calls).activities[1].pages).toContainEqual({
      document_id: DOC_1,
      page: 2,
      repeat_justification: "O mesmo certificado comprova as duas atividades",
    });
  });

  it("a página dona do comprovante (a primeira na ordem) não oferece repetir", async () => {
    const { user } = setup();
    await addShared(user);
    expect(screen.queryByRole("button", { name: "Repetir página 2 de certificado-a.pdf em Algoritmos com justificativa" })).not.toBeInTheDocument();
  });

  it("a repetição guardada mostra a justificativa e pode ser desfeita", async () => {
    const view = layoutView();
    view.layout.activities[1].pages = [{ document_id: DOC_1, page: 2, repeat_justification: "Mesma prova" }];
    const { user } = setup(view);
    const redes = await screen.findByRole("listitem", { name: "Redes" });
    expect(redes).toHaveTextContent("Repetida: Mesma prova");
    await user.click(screen.getByRole("button", { name: "Desfazer repetição da página 2 de certificado-a.pdf em Redes" }));
    expect(screen.getByRole("listitem", { name: "Redes" })).not.toHaveTextContent("Repetida:");
  });
});

describe("ARR-08: arranjo desatualizado", () => {
  it("mostra o aviso em português e o que mudou", async () => {
    const view = layoutView({
      stale: true,
      alerts: [{ code: "ARRANJO_DESATUALIZADO", message: "O arranjo está desatualizado." }],
      staleness: { left_activity_ids: ["x1"], moved_activity_ids: ["x2", "x3"], new_link_activity_ids: [], joined_activity_ids: ["x4"] },
    });
    setup(view);
    expect(await screen.findByText(/O arranjo do Comprovante está desatualizado: as atividades mudaram depois que ele foi salvo/)).toBeInTheDocument();
    expect(screen.getByText("1 saiu · 2 mudaram de item · 1 entrou")).toBeInTheDocument();
  });

  it("marca como inválida a página que aponta para documento ou página que não existe mais", async () => {
    const view = layoutView({ invalid: [{ activity_id: ACT_A, document_id: DOC_1, page: 5 }] });
    setup(view);
    const pages = within(await screen.findByRole("listitem", { name: "Algoritmos" })).getAllByRole("listitem");
    expect(pages[1]).toHaveTextContent("Inválida: o documento ou a página não está mais disponível");
    expect(pages[0]).not.toHaveTextContent("Inválida");
  });

  it("sem aviso do servidor não mostra aviso de arranjo desatualizado", async () => {
    setup();
    await screen.findByRole("listitem", { name: "Algoritmos" });
    expect(screen.queryByText(/desatualizado/)).not.toBeInTheDocument();
  });
});
