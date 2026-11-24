import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScoringRow } from "../api/types";
import { ScoringTable } from "./ScoringTable";

function row(over: Partial<ScoringRow>): ScoringRow {
  return {
    activity_id: "a",
    title: "Palestra",
    activity_status: "VALIDADA",
    evidence_note: null,
    group_number: 2,
    item_number: 7,
    unit_points: "10.00",
    effective_quantity: "4.00",
    formula_text: null,
    points: "40.00",
    pit_hours: null,
    outside_total: false,
    academic_period: null,
    level: null,
    status: "PONTUADA",
    reasons: [],
    alerts: [],
    ...over,
  };
}

const SUBTOTALS = [
  { group_number: 1, subtotal: "0.00" },
  { group_number: 2, subtotal: "40.00" },
];

describe("ScoringTable", () => {
  it("TELA-02: exibe as 7 colunas, na ordem, sem a coluna Comprovante e com nomes curtos", () => {
    render(<ScoringTable rows={[row({})]} subtotals={SUBTOTALS} />);
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual([
      "Grupo",
      "Item",
      "Atividade",
      "Qtde.",
      "Pts. unit.",
      "Total",
      "Status",
    ]);
    expect(screen.queryByRole("columnheader", { name: /Comprovante/ })).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Pts. unit." })).toHaveAttribute("title", "Pontuação unitária");
  });

  it("TELA-02: agrupa as linhas de I a VIII com o subtotal de cada grupo", () => {
    const rows = [
      row({ activity_id: "b", title: "Bancas", group_number: 3, item_number: 2, points: "8.00", unit_points: "8.00", effective_quantity: "1.00" }),
      row({ activity_id: "a", title: "Orientação TCC", group_number: 2 }),
    ];
    render(
      <ScoringTable
        rows={rows}
        subtotals={[...SUBTOTALS, { group_number: 3, subtotal: "8.00" }]}
        groupNames={{ 1: "Docência", 2: "Orientação", 3: "Bancas" }}
      />,
    );
    const groups = screen.getAllByRole("rowgroup").filter((g) => g.tagName === "TBODY");
    const heads = groups.map((g) => within(g).getAllByRole("row")[0].textContent);
    expect(heads[0]).toContain("Grupo I · Docência");
    expect(heads[1]).toContain("Grupo II · Orientação");
    expect(heads[1]).toContain("Subtotal: 40,00");
    expect(heads[2]).toContain("Grupo III · Bancas");
    expect(heads[2]).toContain("Subtotal: 8,00");
    expect(within(groups[1]).getByText("Orientação TCC")).toBeInTheDocument();
    expect(within(groups[2]).queryByText("Orientação TCC")).not.toBeInTheDocument();
  });

  it("TELA-02: mostra grupo, item, quantidade, unitária e total em pt-BR, sem comprovante", () => {
    render(
      <ScoringTable rows={[row({ evidence_note: "Portaria 12/2023" })]} subtotals={SUBTOTALS} groupNames={{ 2: "Orientação" }} />,
    );
    const r = screen.getByText("Palestra").closest("tr")!;
    const cells = within(r).getAllByRole("cell").map((c) => c.textContent);
    expect(cells).toEqual(["II", "7", "Palestra", "4,00", "10,00", "40,00", "Pontuada"]);
  });

  it("TELA-02: a linha não mostra o comprovante, nem 'Sem comprovante'", () => {
    render(<ScoringTable rows={[row({ evidence_note: "Portaria 12/2023" })]} subtotals={SUBTOTALS} />);
    const r = screen.getByText("Palestra").closest("tr")!;
    expect(r).not.toHaveTextContent("Portaria 12/2023");
    expect(r).not.toHaveTextContent("Sem comprovante");
  });

  it("a linha não pontuada ganha o destaque, a rejeitada o sombreado e a pontuada nenhum", () => {
    render(
      <ScoringTable
        rows={[
          row({ activity_id: "a", title: "Validada" }),
          row({ activity_id: "b", title: "Em revisão", status: "POTENCIAL" }),
          row({ activity_id: "c", title: "Sem pontos", status: "NAO_PONTUADA", points: "0.00" }),
          row({ activity_id: "d", title: "Descartada", status: "REJEITADA", points: "0.00" }),
        ]}
        subtotals={SUBTOTALS}
      />,
    );
    const rowOf = (t: string) => screen.getByText(t).closest("tr")!;
    expect(rowOf("Validada")).not.toHaveClass("row-unscored", "row-rejected");
    expect(rowOf("Validada").className).toBe("");
    expect(rowOf("Em revisão")).toHaveClass("row-unscored");
    expect(rowOf("Sem pontos")).toHaveClass("row-unscored");
    expect(rowOf("Descartada")).toHaveClass("row-rejected");
    expect(rowOf("Descartada")).toHaveTextContent("Rejeitada");
    expect(within(rowOf("Descartada")).getAllByRole("cell").map((c) => c.textContent)).toEqual(["II", "7", "Descartada", "—", "—", "—", "Rejeitada"]);
  });

  it("TELA-07: o status mostra PONTUADA, POTENCIAL ou NAO_PONTUADA e as razões em português", () => {
    render(
      <ScoringTable
        rows={[
          row({ activity_id: "p", title: "Curso piloto", status: "POTENCIAL", points: "0.00" }),
          row({ activity_id: "q", title: "Palestra" }),
          row({ activity_id: "n", title: "Fora", status: "NAO_PONTUADA", points: "0.00", reasons: ["FORA_DO_INTERSTICIO", "DUPLICIDADE"] }),
          row({ activity_id: "s", title: "Solta", status: "NAO_PONTUADA", group_number: null, item_number: null, unit_points: null, effective_quantity: null, points: "0.00", reasons: ["SEM_ENQUADRAMENTO"] }),
        ]}
        subtotals={SUBTOTALS}
      />,
    );
    expect(screen.getByText("Curso piloto").closest("tr")).toHaveTextContent("Potencial");
    expect(screen.getByText("Palestra").closest("tr")).toHaveTextContent("Pontuada");
    const fora = screen.getByText("Fora").closest("tr")!;
    expect(fora).toHaveTextContent("Não pontuada");
    expect(fora).toHaveTextContent("Fora do interstício");
    expect(fora).toHaveTextContent("Duplicidade");
    const solta = screen.getByText("Solta").closest("tr")!;
    expect(solta).toHaveTextContent("Sem enquadramento na tabela");
    expect(within(solta).getAllByRole("cell")[0]).toHaveTextContent("—");
  });

  it("TELA-08: cada célula traz o rótulo da coluna para o modo de cartões", () => {
    render(<ScoringTable rows={[row({})]} subtotals={SUBTOTALS} />);
    const r = screen.getByText("Palestra").closest("tr")!;
    const labels = within(r).getAllByRole("cell").map((c) => c.getAttribute("data-label"));
    expect(labels).toEqual([
      "Grupo",
      "Item",
      "Atividade",
      "Quantidade",
      "Pontuação unitária",
      "Total",
      "Status",
    ]);
  });
  describe("TELA-01: Grupo I em horas de PIT", () => {
    const pit = (over: Partial<ScoringRow> = {}) =>
      row({
        activity_id: "g1",
        title: "Cálculo I",
        group_number: 1,
        item_number: 1,
        unit_points: null,
        effective_quantity: null,
        points: "0.00",
        pit_hours: "8.00",
        outside_total: true,
        ...over,
      });
    const G1_SUBTOTALS = [{ group_number: 1, subtotal: "0.00" }, ...SUBTOTALS.slice(1)];

    it("mostra as horas com o rótulo 'horas (PIT)' e nenhum valor em pontos", () => {
      render(<ScoringTable rows={[pit()]} subtotals={G1_SUBTOTALS} />);
      const r = screen.getByText("Cálculo I").closest("tr")!;
      const cells = within(r).getAllByRole("cell").map((c) => c.textContent);
      expect(cells).toEqual(["I", "1", "Cálculo I", "—", "—", "8,00 horas (PIT)", "Pontuada"]);
      expect(r).not.toHaveTextContent("0,00");
    });

    it("rotula a célula de valor como 'horas (PIT)' no modo de cartões", () => {
      render(<ScoringTable rows={[pit()]} subtotals={G1_SUBTOTALS} />);
      const r = screen.getByText("Cálculo I").closest("tr")!;
      const labels = within(r).getAllByRole("cell").map((c) => c.getAttribute("data-label"));
      expect(labels[5]).toBe("horas (PIT)");
    });

    it("troca o subtotal em pontos do Grupo I pelo total de horas de PIT", () => {
      render(<ScoringTable rows={[pit()]} subtotals={G1_SUBTOTALS} group1TotalHours="24.00" />);
      const head = screen.getAllByRole("rowgroup").filter((g) => g.tagName === "TBODY")[0];
      const text = within(head).getAllByRole("row")[0].textContent;
      expect(text).toContain("Total de horas (PIT): 24,00");
      expect(text).not.toContain("Subtotal");
    });

    it("não muda os demais grupos: continuam com o subtotal e a coluna 'Total' em pontos", () => {
      render(<ScoringTable rows={[pit(), row({})]} subtotals={G1_SUBTOTALS} group1TotalHours="8.00" />);
      const groups = screen.getAllByRole("rowgroup").filter((g) => g.tagName === "TBODY");
      expect(within(groups[1]).getAllByRole("row")[0].textContent).toContain("Subtotal: 40,00");
      const r = screen.getByText("Palestra").closest("tr")!;
      const cells = within(r).getAllByRole("cell");
      expect(cells[5]).toHaveTextContent("40,00");
      expect(cells[5].textContent).not.toContain("horas");
      expect(cells[5]).toHaveAttribute("data-label", "Total");
    });

    it("em tabela antiga (sem pit_hours) o Grupo I continua em pontos", () => {
      const old = pit({ pit_hours: null, outside_total: false, unit_points: "10.00", effective_quantity: "9.20", points: "92.00" });
      render(<ScoringTable rows={[old]} subtotals={[{ group_number: 1, subtotal: "92.00" }]} />);
      const r = screen.getByText("Cálculo I").closest("tr")!;
      expect(within(r).getAllByRole("cell")[5]).toHaveTextContent("92,00");
      expect(screen.getAllByRole("rowgroup")[1]).toHaveTextContent("Subtotal: 92,00");
    });

    describe("GI-01, GRES-09: Grupo I que conta no total mostra as ofertas em pontos", () => {
      const counted = (over: Partial<ScoringRow> = {}) =>
        pit({ outside_total: false, points: "8.00", ...over });
      const NEW_SUBTOTALS = [{ group_number: 1, subtotal: "8.00" }, ...SUBTOTALS.slice(1)];

      it("a linha mostra as horas em Quantidade, 1,00 na unitária e os pontos em Total", () => {
        render(<ScoringTable rows={[counted()]} subtotals={NEW_SUBTOTALS} group1TotalHours="8.00" />);
        const r = screen.getByText("Cálculo I").closest("tr")!;
        const cells = within(r).getAllByRole("cell").map((c) => c.textContent);
        expect(cells).toEqual(["I", "1", "Cálculo I", "8,00", "1,00", "8,00", "Pontuada"]);
        expect(cells[5]).not.toContain("horas");
        expect(within(r).getAllByRole("cell")[5]).toHaveAttribute("data-label", "Total");
      });

      it("a faixa do grupo mostra Subtotal, não 'Total de horas (PIT)'", () => {
        render(<ScoringTable rows={[counted()]} subtotals={NEW_SUBTOTALS} group1TotalHours="8.00" />);
        const head = screen.getAllByRole("rowgroup").filter((g) => g.tagName === "TBODY")[0];
        const text = within(head).getAllByRole("row")[0].textContent;
        expect(text).toContain("Subtotal: 8,00");
        expect(text).not.toContain("Total de horas (PIT)");
      });

      it("na versão antiga a linha continua em horas e a faixa em 'Total de horas (PIT)'", () => {
        render(<ScoringTable rows={[pit()]} subtotals={G1_SUBTOTALS} group1TotalHours="8.00" />);
        const r = screen.getByText("Cálculo I").closest("tr")!;
        expect(within(r).getAllByRole("cell")[5]).toHaveTextContent("8,00 horas (PIT)");
        const head = screen.getAllByRole("rowgroup").filter((g) => g.tagName === "TBODY")[0];
        expect(within(head).getAllByRole("row")[0].textContent).toContain("Total de horas (PIT): 8,00");
      });
    });

    it("explica em português a razão CARGA_HORARIA_INSUFICIENTE", () => {
      const short = row({ activity_id: "c", title: "Curso curto", group_number: 4, item_number: 4, status: "NAO_PONTUADA", points: "0.00", reasons: ["CARGA_HORARIA_INSUFICIENTE"] });
      render(<ScoringTable rows={[short]} subtotals={[{ group_number: 4, subtotal: "0.00" }]} />);
      expect(screen.getByText("Curso curto").closest("tr")).toHaveTextContent("Carga horária abaixo do mínimo do item");
    });
  });

  it("UIM-19: a tabela leva as classes das regras de coluna e o título da atividade o texto justificado", () => {
    render(<ScoringTable rows={[row({})]} subtotals={SUBTOTALS} />);
    expect(screen.getByRole("table")).toHaveClass("wide-table", "score-table");
    expect(screen.getByText("Palestra", { selector: "td" })).toHaveClass("text-block");
  });
});
