import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Alert } from "../api/types";
import { AlertList } from "./AlertList";

const WITH_NORM: Alert = {
  code: "INTERSTICIO_INSUFICIENTE",
  severity: "ERRO",
  message: "Interstício menor que o exigido (alerta sintético)",
  norm_reference: "Lei 12.772/2012, art. 12",
  norm_code: "LEI-12772-2012",
  norm_title: "Lei nº 12.772/2012 (texto compilado)",
  norm_url: "https://norma.exemplo.test/lei",
  norm_file_url: null,
  norm_archived: false,
};

const WITHOUT_NORM: Alert = {
  code: "ESTRUTURA_NAO_CADASTRADA",
  severity: "ERRO",
  message: "Estrutura de carreira não cadastrada (alerta sintético)",
  norm_reference: "Regra sem norma cadastrada, art. 3º",
  norm_code: null,
  norm_title: null,
  norm_url: null,
  norm_file_url: null,
  norm_archived: false,
};

function item(text: string) {
  return screen.getByText(text, { exact: false }).closest("li") as HTMLElement;
}

describe("NLINK-03: o alerta mostra a norma que o fundamenta", () => {
  it("com norma mostra o título, a referência e o link 'Ver norma' para a URL", () => {
    render(<AlertList alerts={[WITH_NORM]} />);
    const li = item("Interstício menor que o exigido");
    expect(within(li).getByText("Lei nº 12.772/2012 (texto compilado)")).toBeInTheDocument();
    expect(li).toHaveTextContent("Referência normativa: Lei 12.772/2012, art. 12");
    expect(within(li).getByRole("link", { name: "Ver norma" })).toHaveAttribute(
      "href",
      "https://norma.exemplo.test/lei",
    );
  });

  it("NLINK-04: com arquivo anexado o link vai ao arquivo", () => {
    render(<AlertList alerts={[{ ...WITH_NORM, norm_file_url: "/api/norms/n1/file" }]} />);
    expect(screen.getByRole("link", { name: "Ver norma" })).toHaveAttribute("href", "/api/norms/n1/file");
  });

  it("NBASE-08: a norma arquivada sai com '(arquivada)'", () => {
    render(<AlertList alerts={[{ ...WITH_NORM, norm_archived: true }]} />);
    expect(screen.getByText("(arquivada)")).toBeInTheDocument();
  });
});

describe("NLINK-05: sem norma cadastrada o alerta mostra só o texto de sempre", () => {
  it("mostra a referência e nenhum link nem título de norma", () => {
    render(<AlertList alerts={[WITHOUT_NORM]} />);
    const li = item("Estrutura de carreira não cadastrada");
    expect(li).toHaveTextContent("Referência normativa: Regra sem norma cadastrada, art. 3º");
    expect(within(li).queryByRole("link")).toBeNull();
    expect(within(li).queryByText("Ver norma")).toBeNull();
  });

  it("alerta de uma versão antiga da API, sem os campos da norma, também sai só com o texto", () => {
    const legacy: Alert = {
      code: WITHOUT_NORM.code,
      severity: "ERRO",
      message: WITHOUT_NORM.message,
      norm_reference: WITHOUT_NORM.norm_reference,
    };
    render(<AlertList alerts={[legacy]} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("Referência normativa: Regra sem norma cadastrada, art. 3º")).toBeInTheDocument();
  });
});

describe("NTIT-02: TITULACAO_INSUFICIENTE", () => {
  it("mostra o rótulo, a mensagem do servidor e a norma da regra", () => {
    const titration: Alert = {
      code: "TITULACAO_INSUFICIENTE",
      severity: "ALERTA",
      message: "A classe C (Associado) exige doutorado; a titulação cadastrada do docente é mestrado.",
      norm_reference: "Manual do Servidor da PROGEP, progressão e promoção",
      norm_code: "MANUAL-PROGEP-PROGRESSAO",
      norm_title: "Manual do Servidor (sintético)",
      norm_url: "https://progep.exemplo.test/manual",
      norm_file_url: null,
      norm_archived: false,
    };
    render(<AlertList alerts={[titration]} />);
    expect(screen.getByText("Titulação insuficiente para a classe pretendida")).toBeInTheDocument();
    expect(
      screen.getByText("A classe C (Associado) exige doutorado; a titulação cadastrada do docente é mestrado.", {
        exact: false,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Manual do Servidor (sintético)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver norma" })).toHaveAttribute("href", "https://progep.exemplo.test/manual");
  });
});

describe("NMOV-02: o salto na carreira é ALERTA, nunca estilo de erro", () => {
  it("MODALIDADE_INCOMPATIVEL com severidade ALERTA fica no grupo 'Alerta', sem o estilo de erro", () => {
    const jump: Alert = {
      code: "MODALIDADE_INCOMPATIVEL",
      severity: "ALERTA",
      message:
        "A promoção informada não segue a sequência usual (último nível da classe atual para o primeiro nível da classe seguinte); confira a norma que fundamenta o salto.",
      norm_reference: "Lei 12.772/2012, art. 12",
    };
    const { container } = render(<AlertList alerts={[jump]} />);
    expect(screen.getByRole("heading", { name: "Alerta (1)" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /^Erro/ })).toBeNull();
    expect(container.querySelector(".sev-ERRO")).toBeNull();
    expect(container.querySelector(".sev-ALERTA")).not.toBeNull();
  });
});
