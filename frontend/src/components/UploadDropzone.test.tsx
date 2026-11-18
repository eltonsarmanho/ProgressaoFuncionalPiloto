import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { UploadResult } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { UploadDropzone } from "./UploadDropzone";

const POST = "POST /api/processes/p1/documents";
const pdf = (name: string) => new File(["%PDF-1.4"], name, { type: "application/pdf" });

function result(over: Partial<UploadResult> & { original_name: string; status_code: number }): UploadResult {
  return { document: null, existing_document_id: null, field: null, code: null, message: null, ...over };
}

function setup(routes: Parameters<typeof mockFetch>[0]) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  const onUploaded = vi.fn();
  render(
    <MemoryRouter>
      <UploadDropzone processId="p1" onUploaded={onUploaded} />
    </MemoryRouter>,
  );
  return { ...mock, onUploaded, user: userEvent.setup() };
}

const sentNames = (init: RequestInit | undefined) =>
  (init?.body as FormData).getAll("file").map((f) => (f as File).name);

describe("TELA-02: envio múltiplo", () => {
  it("o seletor é um campo de arquivo múltiplo com rótulo acessível", () => {
    setup({});
    const input = screen.getByLabelText("Selecionar arquivos (PDF, JPG ou PNG)") as HTMLInputElement;
    expect(input.type).toBe("file");
    expect(input.multiple).toBe(true);
    expect(input.accept).toContain(".pdf");
  });

  it("vários arquivos escolhidos no seletor vão numa única requisição multipart com o token CSRF", async () => {
    const { calls, onUploaded, user } = setup({
      [POST]: {
        status: 201,
        body: [result({ original_name: "a.pdf", status_code: 201 }), result({ original_name: "b.pdf", status_code: 201 })],
      },
    });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), [pdf("a.pdf"), pdf("b.pdf")]);

    await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
    expect(calls).toHaveLength(1);
    expect(sentNames(calls[0].init)).toEqual(["a.pdf", "b.pdf"]);
    expect(new Headers(calls[0].init?.headers).get("X-CSRF-Token")).toBe("tok");
  });

  it("vários arquivos soltos na área são enviados do mesmo modo", async () => {
    const { calls, onUploaded } = setup({
      [POST]: {
        status: 201,
        body: [result({ original_name: "c.pdf", status_code: 201 }), result({ original_name: "d.pdf", status_code: 201 })],
      },
    });
    fireEvent.drop(screen.getByTestId("dropzone"), { dataTransfer: { files: [pdf("c.pdf"), pdf("d.pdf")] } });

    await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
    expect(sentNames(calls[0].init)).toEqual(["c.pdf", "d.pdf"]);
  });
});

describe("TELA-05: resultado por arquivo", () => {
  it("207 com 201, 409 e 422: o motivo aparece ao lado de cada arquivo e o enviado não é impedido", async () => {
    const { onUploaded, user } = setup({
      [POST]: {
        status: 207,
        body: [
          result({ original_name: "ok.pdf", status_code: 201 }),
          result({ original_name: "dup.pdf", status_code: 409, existing_document_id: "d-9", message: "Este arquivo já foi enviado neste processo" }),
          result({ original_name: "x.exe", status_code: 422, field: "arquivo", code: "EXTENSAO_INVALIDA", message: "Extensão não permitida" }),
        ],
      },
    });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), [pdf("ok.pdf"), pdf("dup.pdf"), pdf("x.exe")]);

    const list = await screen.findByRole("list", { name: "Resultado do envio" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("ok.pdf: Enviado. Aguardando processamento.");
    expect(items[1]).toHaveTextContent("dup.pdf: Este arquivo já foi enviado neste processo");
    expect(items[2]).toHaveTextContent("x.exe: Extensão não permitida");
    expect(onUploaded).toHaveBeenCalledTimes(1);
  });

  it("409 traz o link para o documento já enviado", async () => {
    const { user } = setup({
      [POST]: {
        status: 207,
        body: [result({ original_name: "dup.pdf", status_code: 409, existing_document_id: "d-9", message: "Este arquivo já foi enviado neste processo" })],
      },
    });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), pdf("dup.pdf"));

    const link = await screen.findByRole("link", { name: "Ver o documento já enviado" });
    expect(link).toHaveAttribute("href", "/processos/p1/documentos?documento=d-9");
  });

  it("429 por arquivo mostra a mensagem de limite e não recarrega a lista", async () => {
    const { onUploaded, user } = setup({
      [POST]: { status: 207, body: [result({ original_name: "z.pdf", status_code: 429, message: "Limite de 60 envios por minuto" })] },
    });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), pdf("z.pdf"));

    expect(await screen.findByRole("listitem")).toHaveTextContent("z.pdf: Limite de 60 envios por minuto");
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("429 sem mensagem mostra o texto padrão de excesso de envios ao lado do arquivo", async () => {
    const { user } = setup({ [POST]: { status: 207, body: [result({ original_name: "z.pdf", status_code: 429 })] } });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), pdf("z.pdf"));

    expect(await screen.findByRole("listitem")).toHaveTextContent(
      "z.pdf: Muitos envios em pouco tempo. Aguarde um minuto e envie de novo.",
    );
  });

  it("VER-11: 413 do nginx (corpo HTML) mostra o limite de envio, não a falha de conexão", async () => {
    const { onUploaded, user } = setup({
      [POST]: { status: 413, raw: "<html><h1>413 Request Entity Too Large</h1></html>" },
    });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), pdf("grande.pdf"));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("O arquivo ou o conjunto excede o limite de envio");
    expect(alert).not.toHaveTextContent("contactar");
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("422 de limite de documentos aparece ao lado do arquivo", async () => {
    const { user } = setup({
      [POST]: { status: 207, body: [result({ original_name: "w.pdf", status_code: 422, field: "limite", message: "O processo já tem 200 documentos" })] },
    });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), pdf("w.pdf"));

    expect(await screen.findByRole("listitem")).toHaveTextContent("w.pdf: O processo já tem 200 documentos");
  });

  it("erro da requisição inteira (processo concluído, 409) vira um alerta", async () => {
    const { onUploaded, user } = setup({ [POST]: { status: 409, body: { detail: "Processo concluído não aceita documentos" } } });
    await user.upload(screen.getByLabelText(/Selecionar arquivos/), pdf("a.pdf"));

    expect(await screen.findByRole("alert")).toHaveTextContent("Processo concluído não aceita documentos");
    expect(onUploaded).not.toHaveBeenCalled();
  });
});
