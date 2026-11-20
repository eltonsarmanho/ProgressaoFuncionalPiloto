import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DossierItem } from "../api/generated";
import { mockFetch } from "../test/fetchMock";
import { DossierOrder } from "./DossierOrder";

const ITEMS: DossierItem[] = [
  { order: 1, title: "Requerimento à CPPD", generated_by: null },
  { order: 2, title: "Portaria da última progressão", generated_by: null },
  { order: 3, title: "Relatório de Atividades", generated_by: "RELATORIO" },
  { order: 4, title: "Tabela de Pontuação", generated_by: "TABELA" },
  { order: 5, title: "Documentação comprobatória", generated_by: "COMPROVANTE" },
  { order: 6, title: "Currículo Lattes atualizado", generated_by: null },
];

function setup(body: DossierItem[] | null = ITEMS) {
  mockFetch({
    "GET /api/dossier-order": body
      ? { status: 200, body }
      : { status: 404, body: { detail: "Não encontrado" } },
  });
  render(<DossierOrder />);
}

describe("ORD-01: lembrete da ordem do dossiê", () => {
  it("mostra a lista na ordem recebida da API, com o número de cada item", async () => {
    setup();
    const list = await screen.findByRole("list", { name: "Ordem de entrega do dossiê" });
    const items = within(list).getAllByRole("listitem");
    expect(items.map((li) => li.getAttribute("value"))).toEqual(["1", "2", "3", "4", "5", "6"]);
    expect(items[0]).toHaveTextContent("Requerimento à CPPD");
    expect(items[5]).toHaveTextContent("Currículo Lattes atualizado");
  });

  it("não reordena: a ordem é a do arquivo de configuração", async () => {
    setup([ITEMS[3], ITEMS[0], ITEMS[2]]);
    const items = within(await screen.findByRole("list", { name: "Ordem de entrega do dossiê" })).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      expect.stringContaining("Tabela de Pontuação"),
      expect.stringContaining("Requerimento à CPPD"),
      expect.stringContaining("Relatório de Atividades"),
    ]);
  });

  it("marca Tabela, Relatório e Comprovante como gerados pelo sistema, e só eles", async () => {
    setup();
    const items = within(await screen.findByRole("list", { name: "Ordem de entrega do dossiê" })).getAllByRole("listitem");
    const marked = items.filter((li) => within(li).queryByText("Gerado pelo sistema"));
    expect(marked.map((li) => li.textContent)).toEqual([
      expect.stringContaining("Relatório de Atividades"),
      expect.stringContaining("Tabela de Pontuação"),
      expect.stringContaining("Documentação comprobatória"),
    ]);
    expect(marked[2]).toHaveTextContent("Comprovante de Documentos");
    expect(items[0]).not.toHaveTextContent("Gerado pelo sistema");
  });

  it("um erro ao ler a lista mostra a mensagem em vez da lista", async () => {
    setup(null);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não encontrado");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});
