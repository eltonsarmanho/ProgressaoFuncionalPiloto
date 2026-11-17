import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { setCsrfToken } from "../api/client";
import type { DocumentSummary } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { DocumentList } from "./DocumentList";

function doc(over: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: "d1",
    process_id: "p1",
    original_name: "declaracao-banca.pdf",
    mime: "application/pdf",
    size_bytes: 3_355_443,
    sha256: "a".repeat(64),
    page_count: 2,
    status: "PROCESSADO",
    status_code: null,
    manual_type: null,
    manual_category: null,
    suggested_type: "DECLARACAO_BANCA",
    suggested_category: "BANCA_MESTRADO",
    confidence: "0.91",
    uploaded_by: "u1",
    uploaded_at: "2026-11-17T10:00:00Z",
    updated_at: "2026-11-17T10:01:00Z",
    version: 3,
    ...over,
  };
}

function setup(documents: DocumentSummary[], routes: Parameters<typeof mockFetch>[0] = {}) {
  setCsrfToken("tok");
  const mock = mockFetch(routes);
  const props = { onView: vi.fn(), onCreateActivity: vi.fn(), onChanged: vi.fn() };
  render(
    <MemoryRouter>
      <DocumentList documents={documents} processId="p1" {...props} />
    </MemoryRouter>,
  );
  return { ...mock, ...props, user: userEvent.setup() };
}

describe("TELA-02: colunas da lista", () => {
  it("mostra nome, tipo, tamanho, status, categoria sugerida e confiança", () => {
    setup([doc()]);
    const row = screen.getByText("declaracao-banca.pdf", { selector: "td" }).closest("tr")!;
    expect(within(row).getByText(/Declaração de banca/)).toBeInTheDocument();
    expect(row).toHaveTextContent("3,2 MB");
    expect(row).toHaveTextContent("Processado");
    expect(row).toHaveTextContent("Banca de mestrado");
    expect(row).toHaveTextContent("sugerida pela IA");
    expect(row).toHaveTextContent("0,91");
    expect(["Nome", "Tipo", "Tamanho", "Status", "Categoria sugerida", "Confiança", "Ações"].map((c) => screen.getByRole("columnheader", { name: c }))).toHaveLength(7);
  });

  it("confiança abaixo de 0,70 é sinalizada; a classificação do usuário aparece como informada por ele", () => {
    setup([doc({ confidence: "0.55" }), doc({ id: "d2", original_name: "m.pdf", manual_type: "CERTIFICADO", manual_category: "PALESTRA" })]);
    expect(screen.getAllByText(/Baixa confiança/)).toHaveLength(1);
    const manual = screen.getByText("m.pdf", { selector: "td" }).closest("tr")!;
    expect(manual).toHaveTextContent("Certificado");
    expect(manual).toHaveTextContent("Palestra, conferência ou mesa-redonda");
    expect(manual).toHaveTextContent("informada por você");
  });

  it("em 360 px a tabela usa a classe de cartões e cada célula tem o rótulo da coluna", () => {
    setup([doc()]);
    const table = screen.getByRole("table");
    expect(table).toHaveClass("scoring-table");
    const row = screen.getByText("declaracao-banca.pdf", { selector: "td" }).closest("tr")!;
    expect(within(row).getAllByRole("cell").map((c) => c.getAttribute("data-label"))).toEqual([
      "Nome", "Tipo", "Tamanho", "Status", "Categoria sugerida", "Confiança", "Ações",
    ]);
  });

  it("sem documentos mostra a mensagem de lista vazia", () => {
    setup([]);
    expect(screen.getByText("Nenhum documento enviado neste processo.")).toBeInTheDocument();
  });
});

describe("TELA-04: ações por documento", () => {
  it("visualizar chama onView e baixar aponta para o endpoint do arquivo", async () => {
    const { onView, user } = setup([doc()]);
    await user.click(screen.getByRole("button", { name: "Visualizar declaracao-banca.pdf" }));
    expect(onView).toHaveBeenCalledWith(expect.objectContaining({ id: "d1" }));
    expect(screen.getByRole("link", { name: "Baixar declaracao-banca.pdf" })).toHaveAttribute("href", "/api/documents/d1/file?download=1");
  });

  it("reprocessar chama a API e recarrega; fica desabilitado enquanto o documento está pendente", async () => {
    const { calls, onChanged, user } = setup([doc(), doc({ id: "d2", original_name: "p.pdf", status: "PENDENTE" })], {
      "POST /api/documents/d1/reprocess": { status: 202, body: doc({ status: "PENDENTE" }) },
    });
    expect(screen.getByRole("button", { name: "Reprocessar p.pdf" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Reprocessar declaracao-banca.pdf" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual(["POST /api/documents/d1/reprocess"]);
  });

  it("substituir envia o arquivo em multipart com a versão esperada e recarrega", async () => {
    const { calls, onChanged, user } = setup([doc()], { "PUT /api/documents/d1/file": { status: 200, body: doc() } });
    await user.click(screen.getByRole("button", { name: "Substituir declaracao-banca.pdf" }));
    await user.upload(screen.getByLabelText("Arquivo substituto"), new File(["%PDF-1.4"], "novo.pdf", { type: "application/pdf" }));

    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    const body = calls[0].init?.body as FormData;
    expect((body.get("file") as File).name).toBe("novo.pdf");
    expect(body.get("expected_version")).toBe("3");
    expect(new Headers(calls[0].init?.headers).get("X-CSRF-Token")).toBe("tok");
  });

  it("substituir por arquivo repetido (409) mostra o motivo e o link do documento existente", async () => {
    const { onChanged, user } = setup([doc()], {
      "PUT /api/documents/d1/file": { status: 409, body: { detail: "Este arquivo já foi enviado neste processo", existing_document_id: "d7" } },
    });
    await user.click(screen.getByRole("button", { name: "Substituir declaracao-banca.pdf" }));
    await user.upload(screen.getByLabelText("Arquivo substituto"), new File(["x"], "igual.pdf", { type: "application/pdf" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Este arquivo já foi enviado neste processo");
    expect(screen.getByRole("link", { name: "Ver o documento já enviado" })).toHaveAttribute("href", "/processos/p1/documentos?documento=d7");
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("excluir exige a justificativa antes de chamar a API e a envia no DELETE", async () => {
    const { calls, onChanged, user } = setup([doc()], { "DELETE /api/documents/d1?justificativa=Enviado%20por%20engano": { status: 204 } });
    await user.click(screen.getByRole("button", { name: "Excluir declaracao-banca.pdf" }));
    await user.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
    expect(await screen.findByText("Informe a justificativa da exclusão.")).toBeInTheDocument();
    expect(calls).toHaveLength(0);

    await user.type(screen.getByLabelText("Justificativa da exclusão"), "Enviado por engano");
    await user.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls[0].method).toBe("DELETE");
  });

  it("classificar manualmente envia tipo, categoria e a versão, e mostra o erro 422 no campo", async () => {
    let attempt = 0;
    const { calls, onChanged, user } = setup([doc({ suggested_type: null, suggested_category: null })], {
      "PUT /api/documents/d1/classification": () => {
        attempt += 1;
        return attempt === 1
          ? { status: 422, body: { detail: [{ field: "categoria", message: "Categoria inválida" }] } }
          : { status: 200, body: doc() };
      },
    });
    await user.click(screen.getByRole("button", { name: "Classificar declaracao-banca.pdf" }));
    await user.selectOptions(screen.getByLabelText("Tipo do documento"), "CERTIFICADO");
    await user.selectOptions(screen.getByLabelText("Categoria da atividade"), "PALESTRA");
    await user.click(screen.getByRole("button", { name: "Salvar classificação" }));
    expect(await screen.findByText("Categoria inválida")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Salvar classificação" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(JSON.parse(calls[1].init?.body as string)).toEqual({ tipo: "CERTIFICADO", categoria: "PALESTRA", expected_version: 3 });
  });
});

describe("TELA-07 / TELA-09: avisos do documento", () => {
  it("EXTRAIDO_SEM_IA mostra o aviso de IA indisponível e a orientação do cadastro manual", () => {
    setup([doc({ status: "EXTRAIDO_SEM_IA", status_code: "IA_INDISPONIVEL", suggested_type: null, suggested_category: null, confidence: null })]);
    const note = screen.getByText(/A IA ficou indisponível/);
    expect(note).toHaveTextContent("cadastre a atividade manualmente");
  });

  it("SEM_ITEM_DE_PONTUACAO mostra o aviso e a ação de criar a atividade deste documento", async () => {
    const { onCreateActivity, user } = setup([doc({ suggested_category: "SEM_ITEM_DE_PONTUACAO", confidence: null })]);
    expect(screen.getByText(/Sem item de pontuação: nenhuma atividade foi criada/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Criar atividade deste documento" }));
    expect(onCreateActivity).toHaveBeenCalledWith(expect.objectContaining({ id: "d1" }));
  });

  it("documento processado com item não mostra a ação de criar atividade", () => {
    setup([doc()]);
    expect(screen.queryByRole("button", { name: "Criar atividade deste documento" })).not.toBeInTheDocument();
  });
});
