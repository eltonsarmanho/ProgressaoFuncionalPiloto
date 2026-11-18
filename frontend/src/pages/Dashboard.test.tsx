import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router";
import { Dashboard } from "./Dashboard";
import { mockFetch } from "../test/fetchMock";

function summary(id: string, name: string, status: string, counts: [number, number, number]) {
  return {
    id,
    status,
    professor_id: `p-${id}`,
    professor_name: name,
    unit_id: "u1",
    modality: "PROMOCAO",
    start_date: "2024-11-23",
    end_date: "2026-11-23",
    interstice: { months: 24, days: 730 },
    alert_counts: { ERRO: counts[0], ALERTA: counts[1], REQUER_ANALISE_NORMATIVA: counts[2] },
  };
}

describe("UI-02: painel", () => {
  it("exibe total, totais por status e contagem de alertas por severidade de cada processo", async () => {
    mockFetch({
      "GET /api/processes": {
        status: 200,
        body: [
          summary("a", "Docente Alfa", "RASCUNHO", [2, 1, 1]),
          summary("b", "Docente Beta", "RASCUNHO", [0, 0, 0]),
          summary("c", "Docente Gama", "EM_ANDAMENTO", [0, 3, 0]),
        ],
      },
    });
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    const totals = await screen.findByRole("region", { name: "Totais" });
    const value = (label: string) =>
      within(totals).getByText(label).closest("div")!.querySelector("dd")!.textContent;
    expect(value("Total de processos")).toBe("3");
    expect(value("Rascunho")).toBe("2");
    expect(value("Em andamento")).toBe("1");
    expect(value("Concluído")).toBe("0");
    expect(value("Arquivado")).toBe("0");

    const alfa = screen.getByRole("listitem", { name: "Docente Alfa" });
    expect(within(alfa).getByText("Erro: 2")).toBeInTheDocument();
    expect(within(alfa).getByText("Alerta: 1")).toBeInTheDocument();
    expect(within(alfa).getByText("Requer análise normativa: 1")).toBeInTheDocument();
    expect(within(alfa).getByRole("link")).toHaveAttribute("href", "/processos/a");

    const gama = screen.getByRole("listitem", { name: "Docente Gama" });
    expect(within(gama).getByText("Em andamento")).toBeInTheDocument();
    expect(within(gama).getByText("Erro: 0")).toBeInTheDocument();
    expect(within(gama).getByText("Alerta: 3")).toBeInTheDocument();
  });
});
