import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { DocumentDetail } from "../api/types";
import { DocumentViewer } from "./DocumentViewer";

function detail(over: Partial<DocumentDetail> = {}): DocumentDetail {
  return {
    id: "d1",
    process_id: "p1",
    original_name: "ata-defesa.pdf",
    mime: "application/pdf",
    size_bytes: 1000,
    sha256: "a".repeat(64),
    page_count: 2,
    status: "PROCESSADO",
    status_code: null,
    manual_type: null,
    manual_category: null,
    suggested_type: "ATA_DEFESA",
    suggested_category: "BANCA_MESTRADO",
    confidence: "0.88",
    uploaded_by: "u1",
    uploaded_at: null,
    updated_at: null,
    version: 1,
    pages: [
      { page_number: 1, method: "TEXTO", char_count: 120, ocr_confidence: null, text: "Ata da defesa <b>de mestrado</b>" },
      { page_number: 2, method: "OCR", char_count: 80, ocr_confidence: "87.50", text: "Assinaturas da banca" },
    ],
    run: { id: "r1", model: "sabia-4-br-sp", duration_ms: 2400, raw_json: { atividades: [{ titulo: "Banca de mestrado" }] }, created_at: null },
    alerts: [{ code: "NAO_ENCONTRADO_NO_TEXTO", field: "event_date", activity_index: 0 }],
    activities: [
      {
        id: "a1",
        title: "Banca de mestrado de Maria",
        group_number: 3,
        item_number: 2,
        source: "SUGERIDA_IA",
        status: "AGUARDANDO_REVISAO",
        version: 1,
        evidences: [{ id: "e1", document_id: "d1", document_name: "ata-defesa.pdf", page: 2, excerpt: "Assinaturas da banca" }],
      },
    ],
    ...over,
  };
}

const view = (d: DocumentDetail, onClose = vi.fn()) => render(<DocumentViewer doc={d} onClose={onClose} />);

describe("TELA-04 / REV-01: visualizador", () => {
  it("mostra o PDF em linha pelo endpoint do arquivo", () => {
    view(detail());
    expect(screen.getByTitle("Documento ata-defesa.pdf")).toHaveAttribute("src", "/api/documents/d1/file");
  });

  it("mostra imagens em linha e oferece só o download para outros tipos de arquivo", () => {
    const { unmount } = view(detail({ mime: "image/png" }));
    expect(screen.getByRole("img", { name: /ata-defesa\.pdf/ })).toHaveAttribute("src", "/api/documents/d1/file");
    unmount();
    view(detail({ mime: "text/plain" }));
    expect(screen.queryByTitle(/Documento/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Baixar ata-defesa.pdf" })).toHaveAttribute("href", "/api/documents/d1/file?download=1");
  });

  it("lista as páginas com método (TEXTO ou OCR) e confiança, e o texto como texto puro", () => {
    view(detail());
    const pages = within(screen.getByRole("heading", { name: "Texto por página" }).parentElement!).getAllByRole("listitem");
    expect(pages).toHaveLength(2);
    expect(screen.getByText(/Página 1 · Método: TEXTO/)).toHaveTextContent("Confiança: não se aplica");
    expect(screen.getByText(/Página 2 · Método: OCR/)).toHaveTextContent("Confiança: 87,50%");
    expect(screen.getByText("Ata da defesa <b>de mestrado</b>")).toBeInTheDocument();
  });

  it("o JSON extraído é somente leitura: aparece formatado e não há campo editável", () => {
    view(detail());
    expect(screen.getByTestId("extracted-json")).toHaveTextContent('"titulo": "Banca de mestrado"');
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "JSON extraído (somente leitura)" })).toBeInTheDocument();
  });

  it("mostra os avisos do documento e deixa claro que o conteúdo é sugestão a revisar", () => {
    view(detail());
    expect(screen.getByText(/Valor não encontrado no texto da página/)).toHaveTextContent("(campo: event_date)");
    expect(screen.getByText(/só uma sugestão/)).toBeInTheDocument();
  });

  it("mostra as atividades ligadas com origem, status, item e a página de origem", () => {
    view(detail());
    const item = screen.getByText("Banca de mestrado de Maria").closest("li")!;
    expect(item).toHaveTextContent("III.2");
    expect(item).toHaveTextContent("Sugerido pela IA");
    expect(item).toHaveTextContent("Aguardando revisão");
    expect(item).toHaveTextContent("ata-defesa.pdf, página 2");
  });

  it("documento em processamento avisa e não mostra páginas; fechar chama onClose", async () => {
    const onClose = vi.fn();
    view(detail({ status: "PROCESSANDO", pages: [], run: null, alerts: [], activities: [] }), onClose);
    expect(screen.getByText("Este documento ainda está sendo processado.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Texto por página" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Fechar visualizador" }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("SEG-03: avisos de data final", () => {
  it("mostra em português a data final calculada do prazo e a data final ausente", () => {
    view(
      detail({
        alerts: [
          { code: "DATA_FIM_DERIVADA", field: "end_date", activity_index: 0 },
          { code: "DATA_FIM_AUSENTE", field: null, activity_index: 1 },
        ],
      }),
    );
    const avisos = screen.getByRole("region", { name: "Avisos" });
    expect(within(avisos).getByText(/Data final calculada do prazo da portaria: confira/)).toBeInTheDocument();
    expect(
      within(avisos).getByText(/Sem data final na portaria: quantidade estimada até o fim do interstício/),
    ).toBeInTheDocument();
    expect(avisos).not.toHaveTextContent("DATA_FIM_DERIVADA");
    expect(avisos).not.toHaveTextContent("DATA_FIM_AUSENTE");
  });
});

describe("SEG-11: avisos de data parcial e de dispensa", () => {
  it("mostra em português a data só com mês e ano e a cláusula de dispensa", () => {
    view(
      detail({
        alerts: [
          { code: "DATA_PARCIAL", field: "event_date", activity_index: 0 },
          { code: "CLAUSULA_DE_DISPENSA", field: null, activity_index: 1 },
        ],
      }),
    );
    const avisos = screen.getByRole("region", { name: "Avisos" });
    expect(within(avisos).getByText(/Data só com mês e ano: confira o período/)).toBeInTheDocument();
    expect(within(avisos).getByText(/Dispensa da função: não vira atividade/)).toBeInTheDocument();
    expect(avisos).not.toHaveTextContent("DATA_PARCIAL");
    expect(avisos).not.toHaveTextContent("CLAUSULA_DE_DISPENSA");
  });
});
