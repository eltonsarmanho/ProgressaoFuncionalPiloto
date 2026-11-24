import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NormLink } from "./NormLink";

const TITLE = "Lei nº 12.772/2012 (texto sintético)";
const FILE = "/api/norms/n1/file";
const URL = "https://norma.exemplo.test/lei";

describe("NLINK-04: NormLink aponta para o arquivo, senão para a URL, senão mostra só o título", () => {
  it("com arquivo e URL o 'Ver norma' vai ao arquivo, nunca à URL", () => {
    render(<NormLink title={TITLE} url={URL} fileUrl={FILE} archived={false} />);
    expect(screen.getByText(TITLE)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver norma" })).toHaveAttribute("href", FILE);
  });

  it("só com URL o 'Ver norma' vai à URL, como link externo seguro", () => {
    render(<NormLink title={TITLE} url={URL} fileUrl={null} archived={false} />);
    const link = screen.getByRole("link", { name: "Ver norma" });
    expect(link).toHaveAttribute("href", URL);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.getAttribute("rel")).toContain("noreferrer");
  });

  it("sem arquivo nem URL mostra só o título, sem link", () => {
    render(<NormLink title={TITLE} url={null} fileUrl={null} archived={false} />);
    expect(screen.getByText(TITLE)).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.queryByText("Ver norma")).toBeNull();
  });
});

describe("NBASE-08: a norma arquivada aparece com '(arquivada)'", () => {
  it("arquivada acrescenta '(arquivada)' e continua com o link", () => {
    render(<NormLink title={TITLE} url={URL} fileUrl={null} archived />);
    expect(screen.getByText("(arquivada)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver norma" })).toHaveAttribute("href", URL);
  });

  it("ativa não mostra '(arquivada)'", () => {
    render(<NormLink title={TITLE} url={URL} fileUrl={null} archived={false} />);
    expect(screen.queryByText("(arquivada)")).toBeNull();
  });
});
