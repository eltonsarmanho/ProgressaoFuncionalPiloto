import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PotentialCards } from "./PotentialCards";

function def(term: string) {
  return screen.getByText(term, { selector: "dt" }).nextElementSibling as HTMLElement;
}

describe("PotentialCards", () => {
  it("GRES-06: com potencial maior que 0 mostra os três cartões com os valores em pt-BR", () => {
    render(<PotentialCards potentialTotal="12.00" potentialDated="8.00" potentialUndated="4.00" />);
    expect(def("Pontuação potencial")).toHaveTextContent("12,00");
    expect(def("Potencial com data no interstício")).toHaveTextContent("8,00");
    expect(def("Potencial sem data — aguardando revisão")).toHaveTextContent("4,00");
  });

  it("GRES-06: com todos os valores em 0 não renderiza nada", () => {
    const { container } = render(<PotentialCards potentialTotal="0.00" potentialDated="0.00" potentialUndated="0.00" />);
    expect(container).toBeEmptyDOMElement();
  });
});
