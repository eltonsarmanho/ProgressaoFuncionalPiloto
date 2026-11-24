import { cleanup, render, screen, within } from "@testing-library/react";
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
  it("BNAV-01: mostra sete etapas habilitadas, com a Etapa 6 Banca e Parecer e a Etapa 7 Requerimento e dossiê, e nenhuma 'em breve'", () => {
    const items = steps({ processId: "p1" });
    expect(items).toHaveLength(7);
    items.forEach((item) => {
      expect(item).not.toHaveTextContent("em breve");
      expect(item).not.toHaveAttribute("aria-disabled");
      expect(within(item).getByRole("link")).toBeInTheDocument();
    });
    expect(items[5]).toHaveTextContent("Etapa 6 · Banca e Parecer");
    expect(items[6]).toHaveTextContent("Etapa 7 · Requerimento e dossiê");
  });

  it("BNAV-01: liga cada etapa à sua rota, a Etapa 6 em /banca e a Etapa 7 em /dossie", () => {
    const hrefs = steps({ processId: "p1" }).map((item) => within(item).getByRole("link").getAttribute("href"));
    expect(hrefs).toEqual([
      "/processos/p1",
      "/processos/p1/documentos",
      "/processos/p1/atividades",
      "/processos/p1/pontuacao",
      "/processos/p1/gerados",
      "/processos/p1/banca",
      "/processos/p1/dossie",
    ]);
  });

  it("BNAV-01: a etapa atual leva aria-current, a 6 e a 7 inclusive", () => {
    [6, 7].forEach((current) => {
      const items = steps({ processId: "p1", current });
      expect(items[current - 1]).toHaveAttribute("aria-current", "step");
      items.filter((_, i) => i !== current - 1).forEach((item) => expect(item).not.toHaveAttribute("aria-current"));
      cleanup();
    });
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

  it("sem processo salvo as etapas habilitadas aparecem sem link, da 2 à 7", () => {
    const items = steps({});
    [1, 2, 3, 4, 5, 6].forEach((i) => {
      expect(within(items[i]).queryByRole("link")).not.toBeInTheDocument();
      expect(items[i]).not.toHaveTextContent("em breve");
    });
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

  it("BNAV-01: o bloqueio fecha também as Etapas 6 e 7, sem link e sem 'em breve'", () => {
    const items = steps({ processId: "p1", current: 3, blocked });
    expect(items).toHaveLength(7);
    [5, 6].forEach((i) => {
      expect(items[i]).toHaveAttribute("aria-disabled", "true");
      expect(items[i]).not.toHaveTextContent("em breve");
      expect(within(items[i]).queryByRole("link")).not.toBeInTheDocument();
    });
    expect(items[5]).toHaveTextContent("Etapa 6 · Banca e Parecer");
    expect(items[6]).toHaveTextContent("Etapa 7 · Requerimento e dossiê");
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

describe("SEC-05, SEC-12: a região viva e os itens fechados", () => {
  const blocked = { step: 3, message: "3 atividades precisam de categoria" };
  const live = () => screen.getByRole("navigation", { name: "Etapas do processo" }).querySelector<HTMLElement>("[aria-live=polite]")!;

  it("a região viva está sempre montada: vazia sem bloqueio e com a mensagem quando há", () => {
    const { unmount } = render(
      <MemoryRouter>
        <StepNav processId="p1" current={3} />
      </MemoryRouter>,
    );
    expect(live()).toBeEmptyDOMElement();
    unmount();
    steps({ processId: "p1", current: 3, blocked });
    expect(live()).toHaveTextContent("3 atividades precisam de categoria");
  });

  it("o <p> da mensagem não tem nós de texto sem bloqueio e mostra a mensagem com bloqueio", () => {
    const { container, unmount } = render(
      <MemoryRouter>
        <StepNav processId="p1" current={3} />
      </MemoryRouter>,
    );
    const empty = container.querySelector(".step-blocked:empty");
    expect(empty).not.toBeNull();
    expect(empty?.id).toBe("step-blocked-message");
    expect(empty?.childNodes).toHaveLength(0);
    unmount();
    const { container: withBlock } = render(
      <MemoryRouter>
        <StepNav processId="p1" current={3} blocked={blocked} />
      </MemoryRouter>,
    );
    expect(withBlock.querySelector(".step-blocked:empty")).toBeNull();
    expect(withBlock.querySelector("p#step-blocked-message")).toHaveTextContent("3 atividades precisam de categoria");
  });

  it("as etapas fechadas, a 6 e a 7 inclusive, apontam a mensagem por aria-describedby; as abertas não", () => {
    const items = steps({ processId: "p1", current: 3, blocked });
    const id = live().id;
    expect(id).not.toBe("");
    [3, 4, 5, 6].forEach((i) => expect(items[i]).toHaveAttribute("aria-describedby", id));
    [0, 1, 2].forEach((i) => expect(items[i]).not.toHaveAttribute("aria-describedby"));
  });
});
