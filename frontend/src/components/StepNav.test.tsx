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

describe("TELA-01: navegação das etapas", () => {
  it("habilita as Etapas 1 a 4 e mantém as 5 a 9 desabilitadas com 'em breve'", () => {
    const items = steps({ processId: "p1" });
    expect(items).toHaveLength(9);
    items.slice(0, 4).forEach((item) => {
      expect(item).not.toHaveTextContent("em breve");
      expect(item).not.toHaveAttribute("aria-disabled");
      expect(within(item).getByRole("link")).toBeInTheDocument();
    });
    items.slice(4).forEach((item, i) => {
      expect(item).toHaveTextContent(`Etapa ${i + 5}`);
      expect(item).toHaveTextContent("em breve");
      expect(item).toHaveAttribute("aria-disabled", "true");
      expect(within(item).queryByRole("link")).not.toBeInTheDocument();
    });
  });

  it("liga cada etapa habilitada à sua rota", () => {
    const hrefs = steps({ processId: "p1" })
      .slice(0, 4)
      .map((item) => within(item).getByRole("link").getAttribute("href"));
    expect(hrefs).toEqual([
      "/processos/p1",
      "/processos/p1/documentos",
      "/processos/p1/atividades",
      "/processos/p1/pontuacao",
    ]);
  });

  it("marca a etapa atual com aria-current e nomeia as Etapas 2 e 3", () => {
    const items = steps({ processId: "p1", current: 3 });
    expect(items[2]).toHaveAttribute("aria-current", "step");
    expect(items[2]).toHaveTextContent("Etapa 3 · Atividades");
    expect(items[1]).toHaveTextContent("Etapa 2 · Documentos");
    expect(items[1]).not.toHaveAttribute("aria-current");
  });

  it("sem processo salvo as etapas habilitadas aparecem sem link", () => {
    const items = steps({});
    expect(within(items[1]).queryByRole("link")).not.toBeInTheDocument();
    expect(items[1]).not.toHaveTextContent("em breve");
  });
});
