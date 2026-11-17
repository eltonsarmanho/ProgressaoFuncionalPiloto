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
  group1_hours_by_period: {},
  group1_total_hours: "0.00",
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

  describe("TELA-02: Grupo I em horas de PIT", () => {
    const OFFICIAL: ScoringResult = {
      ...BASE,
      subtotals: [
        { group_number: 1, subtotal: "0.00" },
        { group_number: 2, subtotal: "52.00" },
        { group_number: 3, subtotal: "7.00" },
        { group_number: 4, subtotal: "62.00" },
        { group_number: 5, subtotal: "0.00" },
        { group_number: 6, subtotal: "30.00" },
        { group_number: 7, subtotal: "4.00" },
        { group_number: 8, subtotal: "56.00" },
      ],
      total: "211.00",
      potential_total: "211.00",
      group1_percent: null,
      group1_hours_by_period: { "2022.1": "24.00", "2022.2": "24.00", "2023.1": "24.00", "2023.2": "20.00" },
      group1_total_hours: "92.00",
      rows: [
        {
          activity_id: "g1", title: "Cálculo I", activity_status: "VALIDADA", evidence_note: null,
          group_number: 1, item_number: 1, unit_points: null, effective_quantity: null, formula_text: null,
          points: "0.00", pit_hours: "8.00", status: "PONTUADA", reasons: [], alerts: [],
        },
      ],
    };

    it("rotula o total como 'Total geral (Grupos II a VIII)' sem incluir o Grupo I", () => {
      render(<ScoringSummary result={OFFICIAL} />);
      expect(def("Total geral (Grupos II a VIII)")).toHaveTextContent("211,00");
      expect(screen.queryByText("Total geral", { selector: "dt" })).not.toBeInTheDocument();
      expect(screen.queryByText("Grupo I · Docência", { selector: "dt" })).not.toBeInTheDocument();
      expect(def("Grupo II · Orientação")).toHaveTextContent("52,00");
    });

    it("mostra à parte as horas de PIT de cada período letivo, em ordem", () => {
      render(<ScoringSummary result={OFFICIAL} />);
      const hours = screen.getByRole("group", { name: "Horas de PIT do Grupo I" });
      const entries = within(hours).getAllByText(/^PIT /, { selector: "dt" }).map((dt) => [dt.textContent, dt.nextElementSibling?.textContent]);
      expect(entries).toEqual([
        ["PIT 2022.1", "24,00 horas"],
        ["PIT 2022.2", "24,00 horas"],
        ["PIT 2023.1", "24,00 horas"],
        ["PIT 2023.2", "20,00 horas"],
      ]);
    });

    it("mostra o total de horas de PIT à parte do total geral", () => {
      render(<ScoringSummary result={OFFICIAL} />);
      const hours = screen.getByRole("group", { name: "Horas de PIT do Grupo I" });
      expect(within(hours).getByText("Total de horas de PIT", { selector: "dt" }).nextElementSibling).toHaveTextContent("92,00 horas");
      expect(def("Total geral (Grupos II a VIII)")).not.toHaveTextContent("92");
    });

    it("sem lançamentos no Grupo I mostra 0,00 hora quando a versão tira o Grupo I do total", () => {
      render(<ScoringSummary result={{ ...OFFICIAL, rows: [], group1_hours_by_period: {}, group1_total_hours: "0.00" }} group1InHours />);
      const hours = screen.getByRole("group", { name: "Horas de PIT do Grupo I" });
      expect(within(hours).getByText("Total de horas de PIT", { selector: "dt" }).nextElementSibling).toHaveTextContent("0,00 horas");
      expect(def("Total geral (Grupos II a VIII)")).toHaveTextContent("211,00");
    });

    it("em tabela antiga o Grupo I segue em pontos e o rótulo continua 'Total geral'", () => {
      render(<ScoringSummary result={BASE} />);
      expect(def("Total geral")).toHaveTextContent("414,00");
      expect(def("Grupo I · Docência")).toHaveTextContent("92,00");
      expect(screen.queryByRole("group", { name: "Horas de PIT do Grupo I" })).not.toBeInTheDocument();
    });
  });
});
