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

describe("SEC-05: avanço bloqueado", () => {
  const blocked = { step: 3, message: "3 atividades precisam de categoria" };

  it("com 'blocked' as Etapas 4 e seguintes ficam desabilitadas, sem link, com aria-disabled", () => {
    const items = steps({ processId: "p1", current: 3, blocked });
    [3, 4].forEach((i) => {
      expect(items[i]).toHaveAttribute("aria-disabled", "true");
      expect(within(items[i]).queryByRole("link")).not.toBeInTheDocument();
    });
    expect(items[3]).toHaveTextContent("Etapa 4 · Pontuação");
    expect(items[4]).toHaveTextContent("Etapa 5 · Documentos gerados");
  });

  it("mostra a mensagem do bloqueio dentro da navegação", () => {
    steps({ processId: "p1", current: 3, blocked });
    const nav = screen.getByRole("navigation", { name: "Etapas do processo" });
    expect(within(nav).getByText("3 atividades precisam de categoria")).toBeInTheDocument();
  });

  it("as etapas até a que bloqueia seguem ativas: a atual, com aria-current, e as anteriores, com link", () => {
    const items = steps({ processId: "p1", current: 3, blocked });
    [0, 1].forEach((i) => {
      expect(items[i]).not.toHaveAttribute("aria-disabled");
      expect(within(items[i]).getByRole("link")).toBeInTheDocument();
    });
    expect(items[2]).toHaveAttribute("aria-current", "step");
    expect(items[2]).not.toHaveAttribute("aria-disabled");
  });

  it("as etapas 6 a 9 seguem 'em breve'", () => {
    const items = steps({ processId: "p1", current: 3, blocked });
    items.slice(5).forEach((item) => expect(item).toHaveTextContent("em breve"));
  });

  it("sem 'blocked' o comportamento não muda e nenhuma mensagem aparece", () => {
    const items = steps({ processId: "p1", current: 3 });
    items.slice(0, 5).forEach((item) => {
      expect(item).not.toHaveAttribute("aria-disabled");
      expect(within(item).getByRole("link")).toBeInTheDocument();
    });
    expect(screen.queryByText(/precisam? de categoria/)).not.toBeInTheDocument();
  });
});
