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

describe("UIM-02 / UIM-03: ações por documento", () => {
  it("os botões têm rótulo curto e o nome do arquivo só vai no aria-label e no title", () => {
    setup([doc()]);
    const row = screen.getByText("declaracao-banca.pdf", { selector: "td" }).closest("tr")!;
    const buttons = within(row).getAllByRole("button");

    expect(buttons.map((b) => b.textContent)).toEqual([
      "Visualizar",
      "Baixar",
      "Substituir",
      "Excluir",
      "Reprocessar",
      "Classificar",
    ]);
    for (const button of buttons) {
      expect(button).toHaveAttribute("aria-label", `${button.textContent} declaracao-banca.pdf`);
      expect(button).toHaveAttribute("title", `${button.textContent} declaracao-banca.pdf`);
    }
    expect(within(row).queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("declaracao-banca.pdf", { selector: "td" })).toHaveAttribute("title", "declaracao-banca.pdf");
  });

  it("UIM-01 / UIM-02: a tabela e a célula do nome levam as classes das regras de coluna e os botões as variantes", () => {
    setup([doc()]);
    expect(screen.getByRole("table")).toHaveClass("wide-table", "doc-table");
    expect(screen.getByText("declaracao-banca.pdf", { selector: "td" })).toHaveClass("doc-name");
    const variant = (name: string) => screen.getByRole("button", { name: `${name} declaracao-banca.pdf` }).className;
    expect(variant("Visualizar")).toContain("btn-primary");
    expect(variant("Excluir")).toContain("btn-danger");
    for (const name of ["Baixar", "Substituir", "Reprocessar", "Classificar"]) {
      expect(variant(name)).toContain("btn-secondary");
    }
  });

  it("UIM-03: Substituir abre o seletor de arquivo (clica o campo de arquivo)", async () => {
    const spy = vi.spyOn(HTMLInputElement.prototype, "click").mockImplementation(() => {});
    const { user } = setup([doc()]);
    await user.click(screen.getByRole("button", { name: "Substituir declaracao-banca.pdf" }));
    expect(spy.mock.instances.some((el) => (el as HTMLInputElement).type === "file")).toBe(true);
    spy.mockRestore();
  });

  it("visualizar chama onView", async () => {
    const { onView, user } = setup([doc()]);
    await user.click(screen.getByRole("button", { name: "Visualizar declaracao-banca.pdf" }));
    expect(onView).toHaveBeenCalledWith(expect.objectContaining({ id: "d1" }));
  });

  it("baixar inicia o download de /api/documents/:id/file?download=1 sem sair da página", async () => {
    const clicked: string[] = [];
    const spy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push(`${this.getAttribute("href")}|${this.hasAttribute("download")}`);
    });
    const { calls, user } = setup([doc()]);

    await user.click(screen.getByRole("button", { name: "Baixar declaracao-banca.pdf" }));

    expect(clicked).toEqual(["/api/documents/d1/file?download=1|true"]);
    expect(calls).toHaveLength(0);
    spy.mockRestore();
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

  it("excluir pede só a confirmação, sem justificativa, e exclui e recarrega", async () => {
    const { calls, onChanged, user } = setup([doc()], { "DELETE /api/documents/d1": { status: 204 } });
    await user.click(screen.getByRole("button", { name: "Excluir declaracao-banca.pdf" }));

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Excluir declaracao-banca.pdf? Esta ação não pode ser desfeita.")).toBeInTheDocument();
    expect(within(dialog).queryByRole("textbox")).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(calls).toHaveLength(0);

    await user.click(within(dialog).getByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual(["DELETE /api/documents/d1"]);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("cancelar a exclusão fecha a confirmação sem chamar a API", async () => {
    const { calls, onChanged, user } = setup([doc()]);
    await user.click(screen.getByRole("button", { name: "Excluir declaracao-banca.pdf" }));

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toHaveLength(0);
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("um erro ao excluir aparece na confirmação e a janela continua aberta", async () => {
    const { onChanged, user } = setup([doc()], { "DELETE /api/documents/d1": { status: 409, body: { detail: "Processo encerrado" } } });
    await user.click(screen.getByRole("button", { name: "Excluir declaracao-banca.pdf" }));

    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Excluir" }));

    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("Processo encerrado");
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("classificar abre uma janela, envia tipo, categoria e a versão, mostra o 422 no campo e fecha ao salvar", async () => {
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
    const dialog = screen.getByRole("dialog", { name: "Classificar documento" });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(within(dialog).queryByLabelText(/justificativa/i)).not.toBeInTheDocument();

    await user.selectOptions(within(dialog).getByLabelText("Tipo do documento"), "CERTIFICADO");
    await user.selectOptions(within(dialog).getByLabelText("Categoria da atividade"), "PALESTRA");
    await user.click(within(dialog).getByRole("button", { name: "Salvar classificação" }));
    expect(await within(dialog).findByText("Categoria inválida")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: "Salvar classificação" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(JSON.parse(calls[1].init?.body as string)).toEqual({ tipo: "CERTIFICADO", categoria: "PALESTRA", expected_version: 3 });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Esc fecha a janela de classificação sem chamar a API e devolve o foco ao botão", async () => {
    const { calls, user } = setup([doc()]);
    const opener = screen.getByRole("button", { name: "Classificar declaracao-banca.pdf" });
    await user.click(opener);

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(calls).toHaveLength(0);
    expect(opener).toHaveFocus();
  });
});

describe("UIM-09: confiança de 70% e avisos reais", () => {
  const row = (name: string) => screen.getByText(name, { selector: "td" }).closest("tr")!;

  it("confiança de 0,70 ou mais, sem aviso real, não mostra aviso nem selo de revisão", () => {
    setup([doc({ original_name: "alta.pdf", confidence: "0.91" }), doc({ id: "d2", original_name: "limite.pdf", confidence: "0.70" })]);
    for (const name of ["alta.pdf", "limite.pdf"]) {
      expect(row(name)).not.toHaveTextContent(/Baixa confiança|revisão|confira/i);
      expect(row(name).querySelector(".doc-warning")).toBeNull();
    }
  });

  it("abaixo de 0,70 mostra o aviso de baixa confiança (0,69 é o limite de baixo)", () => {
    setup([doc({ confidence: "0.69" })]);
    expect(screen.getByText(/Baixa confiança: confira os dados/)).toBeInTheDocument();
  });

  it("aviso real aparece mesmo com confiança alta: texto ilegível, falha e revisão sem código", () => {
    setup([
      doc({ id: "i", original_name: "ilegivel.pdf", status: "REQUER_REVISAO", status_code: "TEXTO_ILEGIVEL", confidence: "0.95" }),
      doc({ id: "f", original_name: "falha.pdf", status: "FALHOU", status_code: "TEMPO_ESGOTADO", confidence: "0.95" }),
      doc({ id: "d", original_name: "divergente.pdf", status: "REQUER_REVISAO", status_code: null, confidence: "0.95" }),
    ]);
    expect(row("ilegivel.pdf")).toHaveTextContent("Texto ilegível");
    expect(row("falha.pdf")).toHaveTextContent("Tempo de leitura esgotado");
    expect(row("divergente.pdf")).toHaveTextContent("Requer revisão: abra o documento e confira os avisos");
  });

  it("a frase de abertura diz que a validação é na Etapa 3, cita os 70% e o descarte dos rascunhos", () => {
    setup([doc()]);
    expect(screen.queryByText(/Tudo que a IA sugere precisa da sua revisão/)).not.toBeInTheDocument();
    const intro = screen.getByText(/validação na Etapa 3/);
    expect(intro).toHaveTextContent("abaixo de 70% ou com aviso merecem uma conferência mais atenta");
    expect(intro).toHaveTextContent("Reprocessar um documento descarta os rascunhos da leitura anterior que você ainda não editou");
  });
});

describe("TELA-07 / TELA-09: avisos do documento", () => {
  it("EXTRAIDO_SEM_IA mostra o aviso de IA indisponível e a orientação do cadastro manual", () => {
    setup([doc({ status: "EXTRAIDO_SEM_IA", status_code: "IA_INDISPONIVEL", suggested_type: null, suggested_category: null, confidence: null })]);
    const note = screen.getByText(/A IA ficou indisponível/);
    expect(note).toHaveTextContent("cadastre a atividade manualmente");
  });

  it("SEM_ITEM_DE_PONTUACAO mostra o aviso e o botão Criar atividade na linha", async () => {
    const { onCreateActivity, user } = setup([doc({ suggested_category: "SEM_ITEM_DE_PONTUACAO", confidence: null })]);
    expect(screen.getByText(/Sem item de pontuação: nenhuma atividade foi criada/)).toBeInTheDocument();
    const row = screen.getByText("declaracao-banca.pdf", { selector: "td" }).closest("tr")!;
    const button = within(row).getByRole("button", { name: "Criar atividade de declaracao-banca.pdf" });
    expect(button).toHaveTextContent("Criar atividade");
    await user.click(button);
    expect(onCreateActivity).toHaveBeenCalledWith(expect.objectContaining({ id: "d1" }));
  });

  it("VER-04: FALHOU por tentativas esgotadas mostra o aviso em português, não o código", () => {
    setup([doc({ status: "FALHOU", status_code: "TENTATIVAS_ESGOTADAS", suggested_type: null, suggested_category: null, confidence: null })]);
    expect(screen.getByText("Tentativas de leitura esgotadas: reprocesse o documento")).toBeInTheDocument();
    expect(screen.queryByText("TENTATIVAS_ESGOTADAS")).not.toBeInTheDocument();
  });

  it("UIM-07: o botão Criar atividade aparece quando o documento não gerou atividade utilizável", () => {
    const no = { suggested_type: null, suggested_category: null, confidence: null };
    setup([
      doc({ id: "f", original_name: "falhou.pdf", status: "FALHOU", status_code: "TENTATIVAS_ESGOTADAS", ...no }),
      doc({ id: "r", original_name: "revisao.pdf", status: "REQUER_REVISAO", status_code: "TEXTO_ILEGIVEL", ...no }),
      doc({ id: "s", original_name: "sem-ia.pdf", status: "EXTRAIDO_SEM_IA", status_code: "IA_INDISPONIVEL", ...no }),
      doc({ id: "n", original_name: "sem-item.pdf", suggested_category: "SEM_ITEM_DE_PONTUACAO" }),
      doc({ id: "z", original_name: "zero.pdf", activity_count: 0 }),
    ]);
    for (const name of ["falhou.pdf", "revisao.pdf", "sem-ia.pdf", "sem-item.pdf", "zero.pdf"]) {
      expect(screen.getByRole("button", { name: `Criar atividade de ${name}` })).toBeInTheDocument();
    }
  });

  it("UIM-07: documento processado com atividade, sem contagem ou ainda em fila não mostra o botão", () => {
    setup([
      doc({ id: "a", original_name: "com-atividade.pdf", activity_count: 1 }),
      doc({ id: "b", original_name: "sem-contagem.pdf" }),
      doc({ id: "c", original_name: "na-fila.pdf", status: "PENDENTE", activity_count: 0, confidence: null }),
    ]);
    expect(screen.queryByRole("button", { name: /Criar atividade/ })).not.toBeInTheDocument();
  });
});

describe("FORA-02 / FORA-04 / FORA-08 / FORA-09: documento fora do interstício", () => {
  const OUTSIDE = "DOCUMENTO_FORA_DO_INTERSTICIO";
  const outside = (over: Partial<DocumentSummary> = {}) =>
    doc({
      id: "o",
      original_name: "antigo.pdf",
      status_code: OUTSIDE,
      suggested_category: null,
      confidence: null,
      activity_count: 0,
      outside_interstice: true,
      document_date: "2022-03-10",
      document_date_precision: "DAY",
      interstice_start: "2024-11-23",
      interstice_end: "2026-11-23",
      ...over,
    });
  const nameCell = (name: string) => screen.getByText(name, { selector: "td" });
  const buttonsOf = (name: string) =>
    within(nameCell(name).closest("tr")!)
      .getAllByRole("button")
      .map((b) => b.textContent);

  it("mostra a faixa com a data do documento e as datas do interstício, na cor de alerta", () => {
    setup([outside()]);
    const banner = screen.getByText(
      "Data do documento 10/03/2022, fora do interstício (23/11/2024 a 23/11/2026): não será processado nas próximas etapas",
    );
    expect(banner.closest("tr")).toHaveClass("doc-outside-banner");
    expect(nameCell("antigo.pdf").closest("tr")).toHaveClass("doc-outside");
  });

  it("com precisão de mês mostra o mês e o ano da data do documento", () => {
    setup([outside({ document_date: "2022-03-01", document_date_precision: "MONTH" })]);
    expect(
      screen.getByText(/^Data do documento 03\/2022, fora do interstício \(23\/11\/2024 a 23\/11\/2026\)/),
    ).toBeInTheDocument();
  });

  it("um documento dentro do período não mostra a faixa", () => {
    setup([doc()]);
    expect(screen.queryByText(/Data do documento/)).not.toBeInTheDocument();
    expect(nameCell("declaracao-banca.pdf").closest("tr")).not.toHaveClass("doc-outside");
  });

  it("a linha só tem Visualizar, Baixar, Excluir e Reprocessar, sem Classificar, Criar atividade nem Substituir", () => {
    setup([outside()]);
    expect(buttonsOf("antigo.pdf")).toEqual(["Visualizar", "Baixar", "Excluir", "Reprocessar"]);
    expect(screen.queryByRole("button", { name: /Criar atividade|Classificar|Substituir/ })).not.toBeInTheDocument();
  });

  it("Reprocessar continua chamando a API e recarrega a lista", async () => {
    const { calls, onChanged, user } = setup([outside()], {
      "POST /api/documents/o/reprocess": { status: 202, body: outside({ status: "PENDENTE" }) },
    });
    await user.click(screen.getByRole("button", { name: "Reprocessar antigo.pdf" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual(["POST /api/documents/o/reprocess"]);
  });

  it("o documento processado fora do período não mostra aviso de revisão nem categoria de item", () => {
    setup([outside()]);
    const row = nameCell("antigo.pdf").closest("tr")!;
    expect(row).toHaveTextContent("Processado");
    expect(row).not.toHaveTextContent(/Requer revisão|Sem item de pontuação|Baixa confiança/);
  });

  it("o resumo conta os documentos, os pendentes de revisão e os fora do interstício", () => {
    setup([
      doc(),
      outside(),
      outside({ id: "o2", original_name: "antigo2.pdf" }),
      doc({ id: "r", original_name: "revisao.pdf", status: "REQUER_REVISAO", status_code: "TEXTO_ILEGIVEL" }),
    ]);
    const summary = screen.getByTestId("doc-summary");
    expect(summary).toHaveTextContent("4 documentos");
    expect(summary).toHaveTextContent("1 pendente de revisão");
    expect(summary).toHaveTextContent("2 fora do interstício");
  });

  it("sem documentos fora do período o resumo mostra 0 fora do interstício", () => {
    setup([doc()]);
    expect(screen.getByTestId("doc-summary")).toHaveTextContent("0 fora do interstício");
  });

  it("não há campo de justificativa na lista nem na faixa", () => {
    setup([outside()]);
    expect(screen.queryByLabelText(/justificativa/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
