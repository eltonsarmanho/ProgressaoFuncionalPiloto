import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Criterion, ScoringGroup } from "../api/types";
import { CategoryPicker } from "./CategoryPicker";

const criterion = (group: number, item: number, description: string): Criterion => ({
  group_number: group, item_number: item, description, unit_label: null, mode: "POR_UNIDADE", unit_points: "4.00",
  hours_per_block: null, weeks_per_semester: null, prep_ratio: null, min_hours: null, max_points: null,
  accepted_evidence: null, rules: null, review_note: null,
});

const GROUPS: ScoringGroup[] = [
  { number: 2, name: "Orientação", counts_in_total: true, max_points: null, criteria: [criterion(2, 5, "Coorientação de mestrado")] },
  {
    number: 3,
    name: "Bancas",
    counts_in_total: true,
    max_points: null,
    criteria: [criterion(3, 1, "Banca de doutorado"), criterion(3, 2, "Banca de mestrado")],
  },
];

describe("SEC-04: CategoryPicker", () => {
  it("lista os itens de cada grupo, sob o nome do grupo", () => {
    render(<CategoryPicker groups={GROUPS} value={null} onChange={vi.fn()} label="Categoria de Banca X" />);
    const bancas = screen.getByRole("group", { name: "III · Bancas" });
    expect(within(bancas).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "III.1 · Banca de doutorado",
      "III.2 · Banca de mestrado",
    ]);
    const orientacao = screen.getByRole("group", { name: "II · Orientação" });
    expect(within(orientacao).getAllByRole("option").map((o) => o.textContent)).toEqual(["II.5 · Coorientação de mestrado"]);
  });

  it("escolher um item chama onChange na hora com o grupo e o item, sem campo de justificativa", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<CategoryPicker groups={GROUPS} value={null} onChange={onChange} label="Categoria de Banca X" />);
    await user.selectOptions(screen.getByRole("combobox", { name: "Categoria de Banca X" }), "3.2");
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ group_number: 3, item_number: 2 });
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
  });

  it("mostra a categoria atual selecionada", () => {
    render(<CategoryPicker groups={GROUPS} value={{ group_number: 3, item_number: 1 }} onChange={vi.fn()} label="Categoria" />);
    expect(screen.getByRole("combobox", { name: "Categoria" })).toHaveValue("3.1");
  });

  it("tem rótulo acessível e o foco chega a ele pelo teclado", async () => {
    const user = userEvent.setup();
    render(<CategoryPicker groups={GROUPS} value={null} onChange={vi.fn()} label="Categoria de Banca X" />);
    await user.tab();
    expect(screen.getByRole("combobox", { name: "Categoria de Banca X" })).toHaveFocus();
  });

  it("sem tabela escolhida, pede para escolher a tabela e não oferece o seletor", () => {
    render(<CategoryPicker groups={[]} value={null} onChange={vi.fn()} label="Categoria" />);
    expect(screen.getByText("Escolha a tabela de pontuação na Etapa 4 para poder escolher a categoria.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("mostra o erro do campo ligado ao seletor", () => {
    render(
      <CategoryPicker groups={GROUPS} value={null} onChange={vi.fn()} label="Categoria" error="Escolha a categoria antes de validar" />,
    );
    const select = screen.getByRole("combobox", { name: "Categoria" });
    expect(select).toHaveAttribute("aria-invalid", "true");
    expect(select).toHaveAccessibleDescription("Escolha a categoria antes de validar");
  });
});
