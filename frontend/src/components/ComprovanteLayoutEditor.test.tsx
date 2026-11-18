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
