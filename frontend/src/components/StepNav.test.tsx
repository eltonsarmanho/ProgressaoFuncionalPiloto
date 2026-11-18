import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { StepNav } from "./StepNav";

function steps(props: Parameters<typeof StepNav>[0]) {
  render(
    <MemoryRouter>
      <StepNav {...props} />
    </MemoryRouter>,
  );
  return within(screen.getByRole("navigation", { name: "Etapas do processo" })).getAllByRole("listitem");
}

describe("TELA-01, UIG-01: navegação das etapas", () => {
  it("habilita as Etapas 1 a 5 e mantém as 6 a 9 desabilitadas com 'em breve'", () => {
    const items = steps({ processId: "p1" });
    expect(items).toHaveLength(9);
    items.slice(0, 5).forEach((item) => {
      expect(item).not.toHaveTextContent("em breve");
      expect(item).not.toHaveAttribute("aria-disabled");
      expect(within(item).getByRole("link")).toBeInTheDocument();
    });
    items.slice(5).forEach((item, i) => {
      expect(item).toHaveTextContent(`Etapa ${i + 6}`);
      expect(item).toHaveTextContent("em breve");
      expect(item).toHaveAttribute("aria-disabled", "true");
      expect(within(item).queryByRole("link")).not.toBeInTheDocument();
    });
  });

  it("liga cada etapa habilitada à sua rota, a Etapa 5 em /gerados", () => {
    const hrefs = steps({ processId: "p1" })
      .slice(0, 5)
      .map((item) => within(item).getByRole("link").getAttribute("href"));
    expect(hrefs).toEqual([
      "/processos/p1",
      "/processos/p1/documentos",
      "/processos/p1/atividades",
      "/processos/p1/pontuacao",
      "/processos/p1/gerados",
    ]);
  });

  it("mostra a Etapa 5 como Documentos gerados e a Etapa 4 segue como Pontuação", () => {
    const items = steps({ processId: "p1", current: 5 });
    expect(items[4]).toHaveTextContent("Etapa 5 · Documentos gerados");
    expect(items[4]).toHaveAttribute("aria-current", "step");
    expect(items[3]).toHaveTextContent("Etapa 4 · Pontuação");
    expect(items[3]).not.toHaveAttribute("aria-current");
  });

  it("marca a etapa atual com aria-current e nomeia as Etapas 2 e 3", () => {
    const items = steps({ processId: "p1", current: 3 });
    expect(items[2]).toHaveAttribute("aria-current", "step");
    expect(items[2]).toHaveTextContent("Etapa 3 · Atividades");
    expect(items[1]).toHaveTextContent("Etapa 2 · Documentos");
    expect(items[1]).not.toHaveAttribute("aria-current");
  });

  it("sem processo salvo as etapas habilitadas aparecem sem link, a 5 inclusive", () => {
    const items = steps({});
    expect(within(items[1]).queryByRole("link")).not.toBeInTheDocument();
    expect(items[1]).not.toHaveTextContent("em breve");
    expect(within(items[4]).queryByRole("link")).not.toBeInTheDocument();
    expect(items[4]).not.toHaveTextContent("em breve");
  });
});
