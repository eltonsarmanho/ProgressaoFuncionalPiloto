import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ActivityFilters, DEFAULT_FILTERS, type ActivityFilterState, type SituationCounts } from "./ActivityFilters";

const COUNTS: SituationCounts = { TODAS: 120, AGUARDANDO: 80, VALIDADAS: 37, PRECISA_CATEGORIA: 3 };

function Harness({ onChange = vi.fn(), initial = DEFAULT_FILTERS }: { onChange?: (f: ActivityFilterState) => void; initial?: ActivityFilterState }) {
  const [filters, setFilters] = useState(initial);
  return (
    <ActivityFilters
      filters={filters}
      counts={COUNTS}
      groups={[3, 2]}
      onChange={(next) => {
        onChange(next);
        setFilters(next);
      }}
    />
  );
}

describe("SEC-03: ActivityFilters", () => {
  it("cada chip de situação mostra a contagem recebida", () => {
    render(<Harness />);
    expect(screen.getByRole("button", { name: "Todas (120)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aguardando validação (80)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validadas (37)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Precisa de categoria (3)" })).toBeInTheDocument();
  });

  it("o padrão marca só 'Todas' com aria-pressed", () => {
    render(<Harness />);
    expect(screen.getByRole("button", { name: "Todas (120)" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Validadas (37)" })).toHaveAttribute("aria-pressed", "false");
  });

  it("clicar num chip o marca e chama onChange com a situação", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Harness onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Validadas (37)" }));
    expect(onChange).toHaveBeenCalledWith({ query: "", situation: "VALIDADAS", group: null });
    expect(screen.getByRole("button", { name: "Validadas (37)" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Todas (120)" })).toHaveAttribute("aria-pressed", "false");
  });

  it("o chip se aciona pelo teclado", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Harness onChange={onChange} />);
    screen.getByRole("button", { name: "Precisa de categoria (3)" }).focus();
    await user.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith({ query: "", situation: "PRECISA_CATEGORIA", group: null });
  });

  it("a busca chama onChange com o texto digitado", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Harness onChange={onChange} />);
    await user.type(screen.getByRole("searchbox", { name: "Buscar por título" }), "banca");
    expect(onChange).toHaveBeenLastCalledWith({ query: "banca", situation: "TODAS", group: null });
  });

  it("o filtro por grupo lista só os grupos presentes, em ordem", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Harness onChange={onChange} />);
    const select = screen.getByRole("combobox", { name: "Filtrar por grupo" });
    expect(Array.from(select.querySelectorAll("option")).map((o) => o.textContent)).toEqual([
      "Todos os grupos",
      "II · Orientação",
      "III · Bancas",
    ]);
    await user.selectOptions(select, "3");
    expect(onChange).toHaveBeenLastCalledWith({ query: "", situation: "TODAS", group: 3 });
  });

  it("limpar volta ao padrão: sem busca, 'Todas' e todos os grupos", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Harness onChange={onChange} initial={{ query: "orient", situation: "VALIDADAS", group: 2 }} />);
    await user.click(screen.getByRole("button", { name: "Limpar filtros" }));
    expect(onChange).toHaveBeenLastCalledWith({ query: "", situation: "TODAS", group: null });
    expect(screen.getByRole("searchbox", { name: "Buscar por título" })).toHaveValue("");
    expect(screen.getByRole("button", { name: "Todas (120)" })).toHaveAttribute("aria-pressed", "true");
  });

  it("sem filtro ativo o botão de limpar não aparece", () => {
    render(<Harness />);
    expect(screen.queryByRole("button", { name: "Limpar filtros" })).not.toBeInTheDocument();
  });
});
