import { describe, expect, it } from "vitest";
import { GENERATION_ALERT_CODES, GENERATION_CODES } from "./api/generated";
import {
  DOCUMENT_CODE_LABELS,
  GENERATION_ALERT_LABELS,
  GENERATION_CODE_LABELS,
  GENERATION_STATE_LABELS,
  OUTSIDE_INTERSTICE_CODE,
} from "./labels";

describe("UIG-05: rótulos em português dos documentos gerados", () => {
  it("todo código de recusa ou falha do design tem rótulo, e só eles", () => {
    expect(Object.keys(GENERATION_CODE_LABELS).sort()).toEqual([...GENERATION_CODES].sort());
    for (const code of GENERATION_CODES) {
      expect(GENERATION_CODE_LABELS[code], code).toBeTruthy();
    }
  });

  it("todo alerta do design tem rótulo, e só eles", () => {
    expect(Object.keys(GENERATION_ALERT_LABELS).sort()).toEqual([...GENERATION_ALERT_CODES].sort());
    for (const code of GENERATION_ALERT_CODES) {
      expect(GENERATION_ALERT_LABELS[code], code).toBeTruthy();
    }
  });

  it("o texto é português legível, nunca o próprio código", () => {
    const texts = [...Object.entries(GENERATION_CODE_LABELS), ...Object.entries(GENERATION_ALERT_LABELS)];
    for (const [code, text] of texts) {
      expect(text, code).not.toBe(code);
      expect(text, code).not.toMatch(/[A-Z]{3,}_[A-Z]/);
      expect(text, code).toMatch(/\s/);
    }
  });

  it("nomeia os três estados da geração", () => {
    expect(GENERATION_STATE_LABELS).toEqual({ GERANDO: "Gerando", PRONTO: "Pronto", FALHOU: "Falhou" });
  });

  it("os códigos pedidos pelo usuário têm o texto que a tela precisa", () => {
    expect(GENERATION_ALERT_LABELS.EXCLUSAO_PARCIAL).toMatch(/excluídos/);
    expect(GENERATION_CODE_LABELS.ARTEFATOS_PENDENTES).toMatch(/Tabela, o Relatório e o Comprovante/);
    expect(GENERATION_CODE_LABELS.ARQUIVO_EXCLUIDO).toMatch(/excluído/);
  });

  it("o rótulo do documento fora do interstício continua valendo", () => {
    expect(DOCUMENT_CODE_LABELS[OUTSIDE_INTERSTICE_CODE]).toBe(
      "Documento fora do interstício: não será processado nas próximas etapas",
    );
  });
});
