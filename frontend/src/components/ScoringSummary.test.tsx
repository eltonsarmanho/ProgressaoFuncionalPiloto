import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScoringResult } from "../api/types";
import { ScoringSummary } from "./ScoringSummary";

const BASE: ScoringResult = {
  process_id: "p",
  chosen: null,
  suggested: null,
  subtotals: [
    { group_number: 1, subtotal: "92.00" },
    { group_number: 2, subtotal: "120.00" },
    { group_number: 3, subtotal: "15.00" },
    { group_number: 4, subtotal: "95.00" },
    { group_number: 5, subtotal: "0.00" },
    { group_number: 6, subtotal: "30.00" },
    { group_number: 7, subtotal: "6.00" },
    { group_number: 8, subtotal: "56.00" },
  ],
  total: "414.00",
  potential_total: "450.50",
  group1_percent: "22.22",
  counters: { activities: 20, with_evidence: 15, pending: 3, not_scored: 4, with_alerts: 6 },
  rows: [],
  limit_adjustments: [],
  alerts: [],
  minimum: { status: "ATINGE", minimum: "100.00", total: "414.00" },
};

function def(term: string) {
  const dt = screen.getByText(term, { selector: "dt" });
  return dt.nextElementSibling as HTMLElement;
}

describe("ScoringSummary", () => {
  it("TELA-03: exibe o subtotal de cada grupo, o total geral e a pontuação potencial em pt-BR", () => {
    render(<ScoringSummary result={BASE} />);
    expect(def("Grupo I · Docência")).toHaveTextContent("92,00");
    expect(def("Grupo II · Orientação")).toHaveTextContent("120,00");
    expect(def("Grupo III · Bancas")).toHaveTextContent("15,00");
    expect(def("Grupo IV · Extensão")).toHaveTextContent("95,00");
    expect(def("Grupo V · Pesquisa")).toHaveTextContent("0,00");
    expect(def("Grupo VI · Administrativas e de Representação")).toHaveTextContent("30,00");
    expect(def("Grupo VII · Capacitação")).toHaveTextContent("6,00");
    expect(def("Grupo VIII · Produção")).toHaveTextContent("56,00");
    expect(def("Total geral")).toHaveTextContent("414,00");
    expect(def("Pontuação potencial")).toHaveTextContent("450,50");
  });

  it("TELA-03: exibe o percentual do Grupo I com vírgula e '—' quando nulo", () => {
    const { rerender } = render(<ScoringSummary result={BASE} />);
    expect(def("Percentual do Grupo I")).toHaveTextContent("22,22%");
    rerender(<ScoringSummary result={{ ...BASE, group1_percent: null }} />);
    expect(def("Percentual do Grupo I")).toHaveTextContent("—");
    expect(def("Percentual do Grupo I")).not.toHaveTextContent("%");
  });

  it("TELA-03: exibe ATINGE com o mínimo, NAO_ATINGE e NAO_DEFINIDO", () => {
    const { rerender } = render(<ScoringSummary result={BASE} />);
    expect(def("Mínimo de referência")).toHaveTextContent("Atinge o mínimo (100,00)");
    rerender(
      <ScoringSummary result={{ ...BASE, minimum: { status: "NAO_ATINGE", minimum: "100.00", total: "99.00" } }} />,
    );
    expect(def("Mínimo de referência")).toHaveTextContent("Não atinge o mínimo (100,00)");
    rerender(
      <ScoringSummary result={{ ...BASE, minimum: { status: "NAO_DEFINIDO", minimum: null, total: "99.00" } }} />,
    );
    expect(def("Mínimo de referência")).toHaveTextContent("Mínimo não definido");
    expect(def("Mínimo de referência")).not.toHaveTextContent("(");
  });

  it("TELA-03: exibe os cinco contadores", () => {
    render(<ScoringSummary result={BASE} />);
    const counters = screen.getByRole("list", { name: "Contadores" });
    const items = within(counters).getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual([
      "Atividades: 20",
      "Com comprovante: 15",
      "Pendentes: 3",
      "Não pontuadas: 4",
      "Com divergências: 6",
    ]);
  });
});
