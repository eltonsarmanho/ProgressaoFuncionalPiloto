import { render, screen } from "@testing-library/react";
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
});
