import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Criterion, ScoringGroup } from "../api/types";
import { ReviewHighlight } from "./ReviewHighlight";

function criterion(item: number, review_note: string | null): Criterion {
  return {
    group_number: 2,
    item_number: item,
    description: `Critério ${item}`,
    unit_label: "unidade",
    mode: "POR_UNIDADE",
    unit_points: "10.00",
    hours_per_block: null,
    weeks_per_semester: null,
    prep_ratio: null,
    min_hours: null,
    max_points: null,
    accepted_evidence: null,
    rules: null,
    review_note,
  };
}

const GROUPS: ScoringGroup[] = [
  {
    number: 2,
    name: "Orientação",
    counts_in_total: true,
    max_points: null,
    criteria: [
      criterion(9, "IFCH: 20 pontos; tabela preenchida: 10"),
      criterion(10, null),
      criterion(12, "Divergência de numeração no Anexo I"),
    ],
  },
];

describe("ADMUI-03: critérios marcados para revisão", () => {
  it("destaca os critérios com anotação e mostra o texto da diferença", () => {
    render(<ReviewHighlight groups={GROUPS} />);

    const marked = screen.getByRole("row", { name: /Critério 9/ });
    expect(marked).toHaveClass("review");
    expect(within(marked).getByText("IFCH: 20 pontos; tabela preenchida: 10")).toBeInTheDocument();
    expect(within(marked).getByText("Revisar")).toBeInTheDocument();
    const other = screen.getByRole("row", { name: /Critério 12/ });
    expect(other).toHaveClass("review");
    expect(other).toHaveTextContent("Divergência de numeração no Anexo I");
  });

  it("não destaca critérios sem anotação", () => {
    render(<ReviewHighlight groups={GROUPS} />);

    const plain = screen.getByRole("row", { name: /Critério 10/ });
    expect(plain).not.toHaveClass("review");
    expect(within(plain).queryByText("Revisar")).not.toBeInTheDocument();
  });

  it("informa quantos critérios estão marcados", () => {
    render(<ReviewHighlight groups={GROUPS} />);

    expect(screen.getByText("2 critérios marcados para revisão humana.")).toBeInTheDocument();
  });

  it("sem marcações não exibe o aviso de revisão", () => {
    render(<ReviewHighlight groups={[{ ...GROUPS[0], criteria: [criterion(10, null)] }]} />);

    expect(screen.queryByText(/marcados? para revisão/)).not.toBeInTheDocument();
    expect(screen.getByText("Critério 10")).toBeInTheDocument();
  });

  it("OFI-06: mostra a carga horária mínima do critério, ou '—' quando não há", () => {
    const withMinimum: ScoringGroup[] = [
      { ...GROUPS[0], criteria: [{ ...criterion(4, null), min_hours: "20.00" }, criterion(6, null)] },
    ];
    render(<ReviewHighlight groups={withMinimum} />);

    expect(screen.getByRole("columnheader", { name: "Carga mínima (h)" })).toBeInTheDocument();
    const four = screen.getByRole("row", { name: /Critério 4/ });
    const minimumCell = (row: HTMLElement) => row.querySelector('td[data-label="Carga mínima (h)"]');
    expect(minimumCell(four)).toHaveTextContent("20,00");
    const six = screen.getByRole("row", { name: /Critério 6/ });
    expect(minimumCell(six)).toHaveTextContent("—");
  });
});
