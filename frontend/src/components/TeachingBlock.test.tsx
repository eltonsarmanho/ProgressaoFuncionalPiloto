import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ScoringRow } from "../api/types";
import { TeachingBlock } from "./TeachingBlock";

function offer(over: Partial<ScoringRow> & { title: string }): ScoringRow {
  return {
    activity_id: over.title,
    activity_status: "VALIDADA",
    evidence_note: null,
    group_number: 1,
    item_number: 1,
    unit_points: null,
    effective_quantity: null,
    formula_text: null,
    points: "8.00",
    pit_hours: "8.00",
    outside_total: false,
    academic_period: "2022.1",
    level: "GRADUACAO",
    status: "PONTUADA",
    reasons: [],
    alerts: [],
    ...over,
  };
}

const ROWS = [
  offer({ title: "Cálculo I", academic_period: "2022.1" }),
  offer({ title: "Álgebra Linear", academic_period: "2022.1", pit_hours: "16.00", points: "16.00" }),
  offer({ title: "Redes de Computadores", academic_period: "2022.2", level: "POS_GRADUACAO", pit_hours: "12.00", points: "12.00", item_number: 2 }),
];
const BY_PERIOD = { "2022.1": "24.00", "2022.2": "12.00" };

const periodBlock = (heading: string) => screen.getByRole("heading", { level: 4, name: heading }).parentElement as HTMLElement;

describe("TeachingBlock", () => {
  it("GRES-04: períodos em ordem, cada oferta com disciplina, nível e horas, e o total do período", () => {
    render(<TeachingBlock rows={ROWS} hoursByPeriod={BY_PERIOD} totalHours="36.00" group1OutsideTotal={false} />);
    const headings = screen.getAllByRole("heading", { level: 4 }).map((h) => h.textContent);
    expect(headings).toEqual(["Período letivo 2022.1", "Período letivo 2022.2"]);

    const first = within(periodBlock("Período letivo 2022.1"));
    const lines = first.getAllByRole("listitem").map((li) => li.textContent);
    expect(lines[0]).toContain("Cálculo I");
    expect(lines[0]).toContain("Graduação");
    expect(lines[0]).toContain("8,00 h");
    expect(lines[1]).toContain("Álgebra Linear");
    expect(lines[1]).toContain("16,00 h");
    expect(first.getByText("Total do período: 24,00 horas")).toBeInTheDocument();

    const second = within(periodBlock("Período letivo 2022.2"));
    expect(second.getByRole("listitem")).toHaveTextContent("Pós-graduação");
    expect(second.getByText("Total do período: 12,00 horas")).toBeInTheDocument();
  });

  it("GRES-04: a oferta aguardando validação leva a etiqueta e o total do período é o da API, sem somá-la", () => {
    const rows = [...ROWS, offer({ title: "Física I", academic_period: "2022.1", status: "POTENCIAL", activity_status: "AGUARDANDO_REVISAO" })];
    render(<TeachingBlock rows={rows} hoursByPeriod={BY_PERIOD} totalHours="36.00" group1OutsideTotal={false} />);
    const first = within(periodBlock("Período letivo 2022.1"));
    const awaiting = first.getAllByRole("listitem").find((li) => li.textContent?.includes("Física I"))!;
    expect(awaiting).toHaveTextContent("Aguardando validação");
    expect(first.getByText("Total do período: 24,00 horas")).toBeInTheDocument();
    expect(screen.queryByText("Total do período: 32,00 horas")).not.toBeInTheDocument();
    expect(screen.getAllByText("Aguardando validação")).toHaveLength(1);
  });

  it("GRES-04: oferta sem período letivo vai para 'Sem período letivo', sem total próprio", () => {
    const rows = [...ROWS, offer({ title: "Seminário", academic_period: null })];
    render(<TeachingBlock rows={rows} hoursByPeriod={BY_PERIOD} totalHours="44.00" group1OutsideTotal={false} />);
    const headings = screen.getAllByRole("heading", { level: 4 }).map((h) => h.textContent);
    expect(headings).toEqual(["Período letivo 2022.1", "Período letivo 2022.2", "Sem período letivo"]);
    const none = within(periodBlock("Sem período letivo"));
    expect(none.getByRole("listitem")).toHaveTextContent("Seminário");
    expect(none.queryByText(/Total do período/)).not.toBeInTheDocument();
  });

  it("GRES-04: o total geral vem da API e, na versão nova, diz '= pontos'", () => {
    render(<TeachingBlock rows={ROWS} hoursByPeriod={BY_PERIOD} totalHours="36.00" group1OutsideTotal={false} />);
    expect(screen.getByText("Total do Grupo I: 36,00 horas = 36,00 pontos")).toBeInTheDocument();
  });

  it("GRES-09: na versão antiga o total diz 'fora do total' e não fala em pontos", () => {
    render(<TeachingBlock rows={ROWS} hoursByPeriod={BY_PERIOD} totalHours="36.00" group1OutsideTotal />);
    expect(screen.getByText("Total do Grupo I: 36,00 horas (fora do total)")).toBeInTheDocument();
    expect(screen.queryByText(/= 36,00 pontos/)).not.toBeInTheDocument();
  });

  it("GRES-05: sem ofertas mostra 'Nenhuma disciplina lançada no Grupo I'", () => {
    render(<TeachingBlock rows={[]} hoursByPeriod={{}} totalHours="0.00" group1OutsideTotal={false} />);
    expect(screen.getByText("Nenhuma disciplina lançada no Grupo I")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 4 })).not.toBeInTheDocument();
    expect(screen.queryByText(/Total do Grupo I/)).not.toBeInTheDocument();
  });

  it("GRES-05: linhas de outros grupos não contam como oferta do Grupo I", () => {
    const other = offer({ title: "Orientação de TCC", group_number: 2, pit_hours: null, academic_period: null, level: null });
    render(<TeachingBlock rows={[other]} hoursByPeriod={{}} totalHours="0.00" group1OutsideTotal={false} />);
    expect(screen.getByText("Nenhuma disciplina lançada no Grupo I")).toBeInTheDocument();
  });

  it("edge case: um período que só tem ofertas fora do interstício (sem linha) não aparece", () => {
    render(<TeachingBlock rows={[ROWS[0]]} hoursByPeriod={{ "2022.1": "8.00", "2019.1": "40.00" }} totalHours="8.00" group1OutsideTotal={false} />);
    const headings = screen.getAllByRole("heading", { level: 4 }).map((h) => h.textContent);
    expect(headings).toEqual(["Período letivo 2022.1"]);
    expect(screen.queryByText(/2019\.1/)).not.toBeInTheDocument();
  });
});
