import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { Norm } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { NormFileForm, NormForm } from "./NormForms";

const NORM: Norm = {
  id: "n1",
  code: "NORMA-SINTETICA-2026",
  title: "Norma sintética de teste",
  kind: "RESOLUCAO",
  issuer: "Órgão sintético",
  published_on: "2026-01-15",
  valid_from: "2026-02-01",
  valid_to: null,
  source_url: "https://norma.exemplo.test/n1",
  notes: null,
  archived: false,
  version: 3,
  file: null,
  linked_rules: [],
};

function lastBody(calls: { init?: RequestInit }[]) {
  return JSON.parse(String(calls[calls.length - 1].init?.body));
}

describe("NBASE-01: cadastrar uma norma", () => {
  it("envia os campos preenchidos, com nulo nos opcionais em branco, e avisa a página", async () => {
    setCsrfToken("csrf-abc");
    const { calls } = mockFetch({ "POST /api/norms": { status: 201, body: NORM } });
    const onSaved = vi.fn();
    render(<NormForm onSaved={onSaved} />);
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Código"), "NORMA-SINTETICA-2026");
    await user.type(screen.getByLabelText("Título"), "Norma sintética de teste");
    await user.selectOptions(screen.getByLabelText("Tipo"), "RESOLUCAO");
    await user.type(screen.getByLabelText("Órgão emissor"), "Órgão sintético");
    await user.type(screen.getByLabelText("Data de publicação"), "2026-01-15");
    await user.type(screen.getByLabelText("Início da vigência (opcional)"), "2026-02-01");
    await user.type(screen.getByLabelText("URL da fonte (opcional)"), "https://norma.exemplo.test/n1");
    await user.click(screen.getByRole("button", { name: "Cadastrar norma" }));

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledWith(NORM));
    expect(lastBody(calls)).toEqual({
      code: "NORMA-SINTETICA-2026",
      title: "Norma sintética de teste",
      kind: "RESOLUCAO",
      issuer: "Órgão sintético",
      published_on: "2026-01-15",
      valid_from: "2026-02-01",
      valid_to: null,
      source_url: "https://norma.exemplo.test/n1",
      notes: null,
    });
  });
});

describe("NBASE-02, 03, 04: o erro 422 aparece no campo certo", () => {
  it("mostra a mensagem de cada campo recusado, marca o campo e não avisa a página", async () => {
    mockFetch({
      "POST /api/norms": {
        status: 422,
        body: {
          detail: [
            { field: "code", message: "Já existe uma norma com este código" },
            { field: "valid_to", message: "Fim da vigência não pode ser anterior ao início" },
            { field: "source_url", message: "URL da fonte deve começar com https:// ou http://" },
          ],
        },
      },
    });
    const onSaved = vi.fn();
    render(<NormForm onSaved={onSaved} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Cadastrar norma" }));

    expect(await screen.findByText("Já existe uma norma com este código")).toBeInTheDocument();
    expect(screen.getByLabelText("Código")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Fim da vigência não pode ser anterior ao início")).toBeInTheDocument();
    expect(screen.getByLabelText("Fim da vigência (opcional)")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("URL da fonte deve começar com https:// ou http://")).toBeInTheDocument();
    expect(screen.getByLabelText("URL da fonte (opcional)")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Título")).not.toHaveAttribute("aria-invalid");
    expect(onSaved).not.toHaveBeenCalled();
  });
});

describe("NBASE-07, 10: editar uma norma", () => {
  it("o código fica só leitura e o PUT leva a versão lida, sem o código", async () => {
    const { calls } = mockFetch({
      "PUT /api/norms/n1": { status: 200, body: { ...NORM, title: "Título novo", version: 4 } },
    });
    const onSaved = vi.fn();
    render(<NormForm norm={NORM} onSaved={onSaved} />);
    const user = userEvent.setup();

    expect(screen.getByLabelText("Código")).toHaveValue("NORMA-SINTETICA-2026");
    expect(screen.getByLabelText("Código")).toHaveAttribute("readonly");

    await user.clear(screen.getByLabelText("Título"));
    await user.type(screen.getByLabelText("Título"), "Título novo");
    await user.click(screen.getByRole("button", { name: "Salvar norma" }));

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    expect(lastBody(calls)).toEqual({
      title: "Título novo",
      kind: "RESOLUCAO",
      issuer: "Órgão sintético",
      published_on: "2026-01-15",
      valid_from: "2026-02-01",
      valid_to: null,
      source_url: "https://norma.exemplo.test/n1",
      notes: null,
      expected_version: 3,
    });
  });

  it("NBASE-10: o 409 mostra que a norma foi alterada por outra pessoa e não avisa a página", async () => {
    mockFetch({ "PUT /api/norms/n1": { status: 409, body: { detail: "Versão desatualizada" } } });
    const onSaved = vi.fn();
    render(<NormForm norm={NORM} onSaved={onSaved} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Salvar norma" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A norma foi alterada por outra pessoa; recarregue",
    );
    expect(onSaved).not.toHaveBeenCalled();
  });
});

describe("NBASE-05, 06: anexar o PDF da norma", () => {
  const PDF = new File(["%PDF-1.4 sintético"], "norma.pdf", { type: "application/pdf" });

  it("envia FormData com o arquivo e a versão esperada, por PUT em /file", async () => {
    setCsrfToken("csrf-abc");
    const { calls } = mockFetch({ "PUT /api/norms/n1/file": { status: 200, body: { ...NORM, version: 4 } } });
    const onSaved = vi.fn();
    render(<NormFileForm norm={NORM} onSaved={onSaved} />);
    const user = userEvent.setup();

    await user.upload(screen.getByLabelText("Arquivo PDF"), PDF);
    await user.click(screen.getByRole("button", { name: "Anexar PDF" }));

    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
    const body = calls[0].init?.body as FormData;
    expect(body).toBeInstanceOf(FormData);
    expect((body.get("file") as File).name).toBe("norma.pdf");
    expect(body.get("expected_version")).toBe("3");
    expect((calls[0].init?.headers as Headers).has("Content-Type")).toBe(false);
  });

  it("diz o limite de 20 MB e mostra a recusa 422 do servidor no campo do arquivo", async () => {
    mockFetch({
      "PUT /api/norms/n1/file": {
        status: 422,
        body: { detail: [{ field: "arquivo", code: "ARQUIVO_GRANDE", message: "O PDF passa do limite de 20 MB." }] },
      },
    });
    const onSaved = vi.fn();
    render(<NormFileForm norm={NORM} onSaved={onSaved} />);
    const user = userEvent.setup();

    expect(screen.getByText("PDF de até 20 MB. Um novo arquivo substitui o anterior.")).toBeInTheDocument();
    await user.upload(screen.getByLabelText("Arquivo PDF"), PDF);
    await user.click(screen.getByRole("button", { name: "Anexar PDF" }));

    expect(await screen.findByText("O PDF passa do limite de 20 MB.")).toBeInTheDocument();
    expect(screen.getByLabelText("Arquivo PDF")).toHaveAttribute("aria-invalid", "true");
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("sem arquivo escolhido pede o PDF e não chama a API", async () => {
    const { fn } = mockFetch({});
    render(<NormFileForm norm={NORM} onSaved={vi.fn()} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Anexar PDF" }));

    expect(await screen.findByText("Selecione o arquivo PDF.")).toBeInTheDocument();
    expect(fn).not.toHaveBeenCalled();
  });

  it("NBASE-10: o 409 mostra que a norma foi alterada por outra pessoa", async () => {
    mockFetch({ "PUT /api/norms/n1/file": { status: 409, body: { detail: "Versão desatualizada" } } });
    render(<NormFileForm norm={NORM} onSaved={vi.fn()} />);
    const user = userEvent.setup();
    await user.upload(screen.getByLabelText("Arquivo PDF"), PDF);
    await user.click(screen.getByRole("button", { name: "Anexar PDF" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A norma foi alterada por outra pessoa; recarregue");
  });
});
