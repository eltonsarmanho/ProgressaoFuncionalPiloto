import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScoringResult } from "../api/types";
import { PanelHeadline } from "./PanelHeadline";

const NEW: Pick<ScoringResult, "total" | "minimum" | "group1_percent"> = {
  total: "303.00",
  minimum: { status: "ATINGE", minimum: "100.00", total: "303.00" },
  group1_percent: "30.36",
};

function def(term: string) {
  return screen.getByText(term, { selector: "dt" }).nextElementSibling as HTMLElement;
}

describe("PanelHeadline", () => {
  it("GRES-01: mostra o total geral em pontos com o rótulo 'Grupos I a VIII'", () => {
    render(<PanelHeadline result={NEW} group1OutsideTotal={false} />);
    expect(def("Total geral")).toHaveTextContent("303,00");
    expect(def("Total geral")).toHaveTextContent("Grupos I a VIII");
  });

  it("GRES-09: na versão antiga o rótulo é 'Grupos II a VIII', nunca o da versão nova", () => {
    render(<PanelHeadline result={{ ...NEW, total: "211.00" }} group1OutsideTotal />);
    expect(def("Total geral")).toHaveTextContent("211,00");
    expect(def("Total geral")).toHaveTextContent("Grupos II a VIII");
    expect(def("Total geral")).not.toHaveTextContent("Grupos I a VIII");
  });

  it("GRES-01: o mínimo atingido e o não atingido saem em texto curto com o valor", () => {
    const { rerender } = render(<PanelHeadline result={NEW} group1OutsideTotal={false} />);
    expect(def("Mínimo de referência")).toHaveTextContent("Atinge o mínimo (100,00)");
    rerender(
      <PanelHeadline
        result={{ ...NEW, total: "99.00", minimum: { status: "NAO_ATINGE", minimum: "100.00", total: "99.00" } }}
        group1OutsideTotal={false}
      />,
    );
    expect(def("Mínimo de referência")).toHaveTextContent("Não atinge o mínimo (100,00)");
  });

  it("GRES-02: sem mínimo definido mostra 'Mínimo não definido' em texto comum, sem a classe de destaque", () => {
    const undefinedMinimum = { ...NEW, minimum: { status: "NAO_DEFINIDO" as const, minimum: null, total: "303.00" } };
    render(<PanelHeadline result={undefinedMinimum} group1OutsideTotal={false} />);
    const value = def("Mínimo de referência");
    expect(value).toHaveTextContent("Mínimo não definido");
    expect(value).not.toHaveTextContent("(");
    expect(value.className).toBe("");
    expect(value.querySelector(".panel-value, .panel-minimum")).toBeNull();
    // Only the total carries the highlight class.
    expect(def("Total geral").querySelector(".panel-value")).not.toBeNull();
  });

  it("GI-08: mantém o percentual do Grupo I sobre o total, com vírgula, e '—' quando não há total", () => {
    const { rerender } = render(<PanelHeadline result={NEW} group1OutsideTotal={false} />);
    expect(def("Percentual do Grupo I")).toHaveTextContent("30,36%");
    rerender(<PanelHeadline result={{ ...NEW, group1_percent: null }} group1OutsideTotal={false} />);
    expect(def("Percentual do Grupo I")).toHaveTextContent("—");
    expect(def("Percentual do Grupo I")).not.toHaveTextContent("%");
  });

  it("NMIN-02: mínimo não definido mostra a explicação da Res. 4.644/2015 e o 'Ver norma' da resolução", () => {
    const withNorm = {
      ...NEW,
      minimum: {
        status: "NAO_DEFINIDO" as const,
        minimum: null,
        total: "303.00",
        norm: {
          code: "RES-4644-2015-CONSEPE",
          title: "Resolução nº 4.644/2015-CONSEPE",
          source_url: "https://sege.exemplo.test/res-4644",
          file_url: null,
          archived: false,
        },
      },
    };
    render(<PanelHeadline result={withNorm} group1OutsideTotal={false} />);
    const value = def("Mínimo de referência");
    expect(value).toHaveTextContent(
      "Mínimo não definido: a Res. 4.644/2015, art. 12, fixa mínimos só para as classes da estrutura antiga",
    );
    expect(value).toHaveTextContent("Resolução nº 4.644/2015-CONSEPE");
    expect(within(value).getByRole("link", { name: "Ver norma" })).toHaveAttribute(
      "href",
      "https://sege.exemplo.test/res-4644",
    );
  });

  it("NMIN-02: com o arquivo da resolução anexado o 'Ver norma' vai ao arquivo", () => {
    const withFile = {
      ...NEW,
      minimum: {
        status: "NAO_DEFINIDO" as const,
        minimum: null,
        total: "303.00",
        norm: {
          code: "RES-4644-2015-CONSEPE",
          title: "Resolução nº 4.644/2015-CONSEPE",
          source_url: "https://sege.exemplo.test/res-4644",
          file_url: "/api/norms/n1/file",
          archived: false,
        },
      },
    };
    render(<PanelHeadline result={withFile} group1OutsideTotal={false} />);
    expect(screen.getByRole("link", { name: "Ver norma" })).toHaveAttribute("href", "/api/norms/n1/file");
  });

  it("NMIN-01/02: o mínimo numérico da estrutura antiga sai como hoje, sem a explicação nem o link", () => {
    render(<PanelHeadline result={NEW} group1OutsideTotal={false} />);
    const value = def("Mínimo de referência");
    expect(value).toHaveTextContent("Atinge o mínimo (100,00)");
    expect(value).not.toHaveTextContent("Res. 4.644/2015");
    expect(screen.queryByRole("link", { name: "Ver norma" })).toBeNull();
  });
});
