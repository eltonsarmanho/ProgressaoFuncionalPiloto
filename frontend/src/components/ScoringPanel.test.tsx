import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScoringResult } from "../api/types";
import { ScoringPanel } from "./ScoringPanel";

// Synthetic derived scenario: group I 92 points of PIT, total 303.
const NEW: ScoringResult = {
  process_id: "p",
  chosen: null,
  suggested: null,
  subtotals: [
    { group_number: 1, subtotal: "92.00" },
    { group_number: 2, subtotal: "52.00" },
    { group_number: 3, subtotal: "7.00" },
    { group_number: 4, subtotal: "62.00" },
    { group_number: 5, subtotal: "0.00" },
    { group_number: 6, subtotal: "30.00" },
    { group_number: 7, subtotal: "4.00" },
    { group_number: 8, subtotal: "56.00" },
  ],
  total: "303.00",
  potential_total: "12.00",
  potential_dated: "8.00",
  potential_undated: "4.00",
  group1_percent: "30.36",
  group1_hours_by_period: { "2022.1": "24.00", "2022.2": "24.00", "2023.1": "24.00", "2023.2": "20.00" },
  group1_total_hours: "92.00",
  counters: { activities: 20, with_evidence: 15, pending: 3, not_scored: 4, with_alerts: 6 },
  rows: [
    {
      activity_id: "g1", title: "Cálculo I", activity_status: "VALIDADA", evidence_note: null,
      group_number: 1, item_number: 1, unit_points: null, effective_quantity: null, formula_text: null,
      points: "8.00", pit_hours: "8.00", outside_total: false, academic_period: "2022.1", level: "GRADUACAO",
      status: "PONTUADA", reasons: [], alerts: [],
    },
  ],
  limit_adjustments: [],
  alerts: [],
  minimum: { status: "ATINGE", minimum: "100.00", total: "303.00" },
};

const OLD: ScoringResult = {
  ...NEW,
  total: "211.00",
  group1_percent: "0.00",
  subtotals: NEW.subtotals.map((s) => (s.group_number === 1 ? { ...s, subtotal: "0.00" } : s)),
  rows: NEW.rows.map((r) => ({ ...r, points: "0.00", outside_total: true })),
  minimum: { status: "ATINGE", minimum: "100.00", total: "211.00" },
};

const headings = () => screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);

describe("ScoringPanel", () => {
  it("GRES-07: os blocos aparecem na ordem: faixa, barras, Docência, potencial e contadores, cada um numa seção com título", () => {
    render(<ScoringPanel result={NEW} group1OutsideTotal={false} />);
    expect(headings()).toEqual(["Resultado", "Pontos por grupo", "Docência (PIT)", "Potencial", "Contadores"]);
    for (const name of headings()) {
      expect(screen.getByRole("region", { name: name! })).toBeInTheDocument();
    }
    expect(within(screen.getByRole("region", { name: "Resultado" })).getByText("Total geral")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Pontos por grupo" })).getAllByRole("listitem")).toHaveLength(8);
    expect(within(screen.getByRole("region", { name: "Docência (PIT)" })).getByText("Cálculo I")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Potencial" })).getByText("Pontuação potencial", { selector: "dt" })).toBeInTheDocument();
  });

  it("GRES-07: os contadores são uma lista única com os cinco contadores", () => {
    render(<ScoringPanel result={NEW} group1OutsideTotal={false} />);
    const counters = screen.getByRole("list", { name: "Contadores" });
    expect(within(counters).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Atividades: 20",
      "Com comprovante: 15",
      "Pendentes: 3",
      "Não pontuadas: 4",
      "Com divergências: 6",
    ]);
  });

  it("GRES-06: sem potencial a seção do potencial não aparece", () => {
    render(
      <ScoringPanel result={{ ...NEW, potential_total: "0.00", potential_dated: "0.00", potential_undated: "0.00" }} group1OutsideTotal={false} />,
    );
    expect(headings()).toEqual(["Resultado", "Pontos por grupo", "Docência (PIT)", "Contadores"]);
  });

  it("GRES-09: a versão antiga mostra 'Grupos II a VIII', sem barra do Grupo I, e a Docência fora do total", () => {
    render(<ScoringPanel result={OLD} group1OutsideTotal />);
    expect(screen.getByText("Total geral", { selector: "dt" }).nextElementSibling).toHaveTextContent("Grupos II a VIII");
    expect(within(screen.getByRole("region", { name: "Pontos por grupo" })).getAllByRole("listitem")).toHaveLength(7);
    expect(screen.getByText(/\(fora do total\)/)).toBeInTheDocument();
  });

  it("sem critério de carga semanal no Grupo I (tabela de outro tipo) não há bloco Docência", () => {
    render(<ScoringPanel result={{ ...NEW, rows: [] }} group1OutsideTotal={false} group1Load={false} />);
    expect(headings()).not.toContain("Docência (PIT)");
  });

  it("GRES-08: o painel não tem elemento focável próprio", () => {
    const { container } = render(<ScoringPanel result={NEW} group1OutsideTotal={false} />);
    expect(container.querySelector("a, button, input, select, textarea, [tabindex]")).toBeNull();
  });

  describe("região viva do total", () => {
    const status = () => screen.getByRole("status");

    it("fica montada e vazia na abertura", () => {
      render(<ScoringPanel result={NEW} group1OutsideTotal={false} />);
      expect(status()).toBeInTheDocument();
      expect(status()).toBeEmptyDOMElement();
    });

    it("anuncia o total novo depois de um recálculo que o muda", () => {
      const { rerender } = render(<ScoringPanel result={NEW} group1OutsideTotal={false} />);
      rerender(<ScoringPanel result={{ ...NEW, total: "311.00" }} group1OutsideTotal={false} />);
      expect(status()).toHaveTextContent("Total geral atualizado: 311,00 pontos");
    });

    it("não anuncia quando o total não muda", () => {
      const { rerender } = render(<ScoringPanel result={NEW} group1OutsideTotal={false} />);
      rerender(<ScoringPanel result={{ ...NEW, counters: { ...NEW.counters, pending: 2 } }} group1OutsideTotal={false} />);
      expect(status()).toBeEmptyDOMElement();
    });
  });
});
