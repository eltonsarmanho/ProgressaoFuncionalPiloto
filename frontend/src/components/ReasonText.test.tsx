import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { InvalidReason, Validity } from "../api/types";
import { ReasonText } from "./ReasonText";

const INTERSTICE = { interstice_start: "2024-01-01", interstice_end: "2025-12-31" };
const invalid = (reason: InvalidReason, params: Validity["params"] = {}): Validity => ({
  state: "NAO_VALIDA",
  reason,
  needs_category: false,
  params,
});

describe("SEC-07: ReasonText escreve o motivo da atividade não válida", () => {
  it("fora do interstício por data usa a data e o interstício dos parâmetros", () => {
    render(<ReasonText validity={invalid("FORA_DO_INTERSTICIO", { event_date: "2023-03-15", ...INTERSTICE })} />);
    expect(screen.getByText("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025")).toBeInTheDocument();
  });

  it("fora do interstício de categoria por ano usa o início e o fim do período", () => {
    render(
      <ReasonText
        validity={invalid("FORA_DO_INTERSTICIO", { period_start: "2022-01-10", period_end: "2022-12-20", ...INTERSTICE })}
      />,
    );
    expect(
      screen.getByText("Fora do interstício: período 10/01/2022 a 20/12/2022; interstício 01/01/2024 a 31/12/2025"),
    ).toBeInTheDocument();
  });

  it("carga horária insuficiente mostra as horas lidas e o mínimo do item", () => {
    render(<ReasonText validity={invalid("CARGA_HORARIA_INSUFICIENTE", { hours: "19", min_hours: "20" })} />);
    expect(screen.getByText("Carga horária insuficiente: 19 h; o item exige 20 h")).toBeInTheDocument();
  });

  it("rejeitada diz 'Rejeitada por você'", () => {
    render(<ReasonText validity={invalid("REJEITADA")} />);
    expect(screen.getByText("Rejeitada por você")).toBeInTheDocument();
  });

  it("o motivo é texto na página, não só cor: o elemento tem o texto e nenhum rótulo vazio", () => {
    const { container } = render(<ReasonText validity={invalid("GRUPO_NAO_CONTA")} />);
    expect(container.textContent).toBe("Grupo não conta no total");
  });

  it("uma atividade válida não escreve motivo", () => {
    const valid: Validity = { state: "VALIDA", reason: null, needs_category: false, params: {} };
    const { container } = render(<ReasonText validity={valid} />);
    expect(container).toBeEmptyDOMElement();
  });
});
