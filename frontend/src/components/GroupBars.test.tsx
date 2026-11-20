import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GroupBars } from "./GroupBars";

// Synthetic derived scenario: group I 92 points, total 303.
const SUBTOTALS = [
  { group_number: 1, subtotal: "92.00" },
  { group_number: 2, subtotal: "52.00" },
  { group_number: 3, subtotal: "7.00" },
  { group_number: 4, subtotal: "62.00" },
  { group_number: 5, subtotal: "0.00" },
  { group_number: 6, subtotal: "30.00" },
  { group_number: 7, subtotal: "4.00" },
  { group_number: 8, subtotal: "56.00" },
];

const items = () => within(screen.getByRole("list", { name: "Pontos por grupo" })).getAllByRole("listitem");
const bar = (li: HTMLElement) => li.querySelector<HTMLElement>(".group-bar-track")!;
const fill = (li: HTMLElement) => li.querySelector<HTMLElement>(".group-bar-fill")!;

describe("GroupBars", () => {
  it("GRES-03: uma linha por grupo de I a VIII na versão nova, com o nome curto e o valor em texto", () => {
    render(<GroupBars subtotals={SUBTOTALS} total="303.00" group1OutsideTotal={false} />);
    const lines = items();
    expect(lines).toHaveLength(8);
    expect(lines[0]).toHaveTextContent("I · Docência");
    expect(lines[0]).toHaveTextContent("92,00");
    expect(lines[5]).toHaveTextContent("VI · Administrativas e de Representação");
    expect(lines[5]).toHaveTextContent("30,00");
    expect(lines[7]).toHaveTextContent("VIII · Produção");
    expect(lines[7]).toHaveTextContent("56,00");
  });

  it("GRES-09: na versão antiga o grupo I não tem barra (sete linhas, de II a VIII)", () => {
    render(<GroupBars subtotals={SUBTOTALS} total="211.00" group1OutsideTotal />);
    const lines = items();
    expect(lines).toHaveLength(7);
    expect(lines[0]).toHaveTextContent("II · Orientação");
    expect(screen.queryByText(/Docência/)).not.toBeInTheDocument();
  });

  it("GRES-03, GRES-08: a barra é decorativa (aria-hidden) e tem largura proporcional ao total", () => {
    render(<GroupBars subtotals={SUBTOTALS} total="303.00" group1OutsideTotal={false} />);
    const first = items()[0];
    expect(bar(first)).toHaveAttribute("aria-hidden", "true");
    expect(parseFloat(fill(first).style.width)).toBeCloseTo(30.36, 1);
    expect(fill(first).style.width.endsWith("%")).toBe(true);
    expect(parseFloat(fill(items()[1]).style.width)).toBeCloseTo((52 / 303) * 100, 1);
  });

  it("GRES-03: grupo com 0,00 sai em tom discreto (muted) e com o valor em texto", () => {
    render(<GroupBars subtotals={SUBTOTALS} total="303.00" group1OutsideTotal={false} />);
    const lines = items();
    expect(lines[4]).toHaveClass("muted");
    expect(lines[4]).toHaveTextContent("0,00");
    expect(lines[0]).not.toHaveClass("muted");
  });

  it("GRES-03: total 0 dá barra vazia, sem NaN nem Infinity", () => {
    const zero = SUBTOTALS.map((s) => ({ ...s, subtotal: "0.00" }));
    const { container } = render(<GroupBars subtotals={zero} total="0.00" group1OutsideTotal={false} />);
    for (const li of items()) {
      expect(fill(li).style.width).toBe("0%");
      expect(li).toHaveClass("muted");
    }
    expect(container.innerHTML).not.toMatch(/NaN|Infinity/);
  });
});
