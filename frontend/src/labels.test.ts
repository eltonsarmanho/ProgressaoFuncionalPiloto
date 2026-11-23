import { describe, expect, it } from "vitest";
import {
  BOARD_ROLES,
  CHECKLIST_STATES,
  ORDINANCE_WARNING_CODES,
  READING_CODES,
  READING_STATES,
  VALUE_SOURCES,
} from "./api/board";
import { ARTIFACT_KINDS, DOCUMENT_KINDS, GENERATION_ALERT_CODES, GENERATION_CODES, PENDING_BOARD_ITEMS } from "./api/generated";
import { BLOCK_REASON_CODES, SCORING_ALERT_CODES, type InvalidReason, type Validity } from "./api/types";
import {
  ALERT_CODE_LABELS,
  BADGE_AWAITING_VALIDATION,
  BADGE_NEEDS_CATEGORY,
  GROUP_NAMES,
  INVALID_REASON_LABELS,
  LEVEL_LABELS,
  MINIMUM_LABELS,
  PANEL_LABELS,
  invalidReasonText,
  needsCategoryMessage,
  DOCUMENT_CODE_LABELS,
  BOARD_ROLE_LABELS,
  CHECKLIST_STATE_LABELS,
  DOCUMENT_KIND_LABELS,
  ORDINANCE_WARNING_LABELS,
  READING_CODE_LABELS,
  READING_STATE_LABELS,
  VALUE_SOURCE_LABELS,
  PENDING_BOARD_LABELS,
  GENERATION_ALERT_LABELS,
  GENERATION_CODE_LABELS,
  GENERATION_STATE_LABELS,
  OUTSIDE_INTERSTICE_CODE,
  alertDetail,
  alertText,
  BLOCK_REASON_LABELS,
  HISTORY_ACTION_LABELS,
  HISTORY_ENTITY_LABELS,
  TABLE_BADGE_LABELS,
  blockReasonText,
  historyChangeLabel,
  inUseBadge,
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

describe("UIG-05, REL-05: o texto dos alertas não repete o rótulo nem engana", () => {
  it("o alerta de atividades fora do documento mostra só as contagens depois do rótulo", () => {
    const alert = { code: "ATIVIDADES_FORA_DO_DOCUMENTO", message: "Atividades fora do documento: 1 sem enquadramento; 2 aguardando revisão." } as const;
    expect(alertDetail(alert)).toBe("1 sem enquadramento; 2 aguardando revisão.");
    expect(alertText(alert)).toBe("Há atividades que ficaram fora do documento");
  });

  it("a redação recusada leva os motivos no próprio texto e nada depois", () => {
    const alert = { code: "REDACAO_REJEITADA", message: "NUMERO,DATA" } as const;
    expect(alertText(alert)).toContain("(número que não está na atividade, data que não está na atividade)");
    expect(alertDetail(alert)).toBe("");
  });

  it("a redação indisponível não diz que faltou tempo: vale para chave ausente, erro e prazo", () => {
    const text = alertText({ code: "REDACAO_INDISPONIVEL", message: "" });
    expect(text).toBe("A IA não está disponível agora: ficou o texto-modelo");
    expect(text).not.toMatch(/a tempo/);
  });

  it("um alerta sem texto a mais não mostra detalhe", () => {
    expect(alertDetail({ code: "ATIVIDADE_SEM_COMPROVANTE", message: "" })).toBe("");
    expect(alertDetail({ code: "PAGINA_RASTERIZADA", message: "Documento 1, página 2" })).toBe("Documento 1, página 2");
  });
});

const INTERSTICE = { interstice_start: "2024-01-01", interstice_end: "2025-12-31" };
const invalid = (reason: InvalidReason, params: Validity["params"] = {}): Validity => ({
  state: "NAO_VALIDA",
  reason,
  needs_category: false,
  params,
});

describe("SEC-07: o texto de cada motivo de atividade não válida", () => {
  it("fora do interstício por data: 'Fora do interstício: data dd/mm/aaaa; interstício dd/mm/aaaa a dd/mm/aaaa'", () => {
    const text = invalidReasonText(invalid("FORA_DO_INTERSTICIO", { event_date: "2023-03-15", ...INTERSTICE }));
    expect(text).toBe("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025");
  });

  it("fora do interstício por período (categoria medida por ano) usa início e fim", () => {
    const text = invalidReasonText(
      invalid("FORA_DO_INTERSTICIO", { period_start: "2022-01-10", period_end: "2022-12-20", ...INTERSTICE }),
    );
    expect(text).toBe("Fora do interstício: período 10/01/2022 a 20/12/2022; interstício 01/01/2024 a 31/12/2025");
  });

  it("GI-09, GRES-04: oferta só com período letivo diz 'período letivo AAAA.N' e o interstício", () => {
    const text = invalidReasonText(invalid("FORA_DO_INTERSTICIO", { academic_period: "2019.1", ...INTERSTICE }));
    expect(text).toBe("Fora do interstício: período letivo 2019.1; interstício 01/01/2024 a 31/12/2025");
  });

  it("GI-09: com data, o texto continua o da data, mesmo se a atividade também tem período letivo", () => {
    const text = invalidReasonText(
      invalid("FORA_DO_INTERSTICIO", { event_date: "2023-03-15", academic_period: "2023.1", ...INTERSTICE }),
    );
    expect(text).toBe("Fora do interstício: data 15/03/2023; interstício 01/01/2024 a 31/12/2025");
  });

  it("carga horária insuficiente: 'Carga horária insuficiente: N h; o item exige M h'", () => {
    expect(invalidReasonText(invalid("CARGA_HORARIA_INSUFICIENTE", { hours: "19", min_hours: "20" }))).toBe(
      "Carga horária insuficiente: 19 h; o item exige 20 h",
    );
  });

  it("as horas decimais saem com vírgula", () => {
    expect(invalidReasonText(invalid("CARGA_HORARIA_INSUFICIENTE", { hours: "19.5", min_hours: "20" }))).toBe(
      "Carga horária insuficiente: 19,5 h; o item exige 20 h",
    );
  });

  it("rejeitada: 'Rejeitada por você'", () => {
    expect(invalidReasonText(invalid("REJEITADA"))).toBe("Rejeitada por você");
  });

  it("os motivos sem parâmetros também têm texto, e nenhum é o próprio código", () => {
    const reasons: InvalidReason[] = ["REJEITADA", "FORA_DO_INTERSTICIO", "CARGA_HORARIA_INSUFICIENTE", "GRUPO_NAO_CONTA", "DUPLICIDADE"];
    for (const reason of reasons) {
      expect(INVALID_REASON_LABELS[reason], reason).not.toMatch(/[A-Z]{3,}_[A-Z]|^[A-Z]+$/);
      expect(invalidReasonText(invalid(reason)), reason).not.toBe(reason);
    }
    expect(invalidReasonText(invalid("GRUPO_NAO_CONTA"))).toBe("Grupo não conta no total");
    expect(invalidReasonText(invalid("DUPLICIDADE"))).toBe("Duplicidade");
  });

  it("os nomes curtos dos motivos servem à contagem do título da seção", () => {
    expect(INVALID_REASON_LABELS).toEqual({
      REJEITADA: "Rejeitada por você",
      FORA_DO_INTERSTICIO: "Fora do interstício",
      CARGA_HORARIA_INSUFICIENTE: "Carga horária insuficiente",
      GRUPO_NAO_CONTA: "Grupo não conta no total",
      DUPLICIDADE: "Duplicidade",
    });
  });
});

describe("SEC-04, SEC-05: selos e mensagem do bloqueio", () => {
  it("os selos têm o texto da spec", () => {
    expect(BADGE_NEEDS_CATEGORY).toBe("Precisa de categoria");
    expect(BADGE_AWAITING_VALIDATION).toBe("Aguardando validação");
  });

  it("'N atividades precisam de categoria', com o singular", () => {
    expect(needsCategoryMessage(3)).toBe("3 atividades precisam de categoria");
    expect(needsCategoryMessage(1)).toBe("1 atividade precisa de categoria");
  });
});

describe("SEG-05, VAL-02: códigos novos têm rótulo", () => {
  it("a recusa ATIVIDADE_SEM_CATEGORIA diz onde resolver", () => {
    expect(GENERATION_CODE_LABELS.ATIVIDADE_SEM_CATEGORIA).toBe(
      "Há atividades sem categoria na Etapa 3. Escolha a categoria de cada uma.",
    );
  });

  it("o alerta QUANTIDADE_ASSUMIDA existe na lista de códigos e tem rótulo", () => {
    expect(SCORING_ALERT_CODES).toContain("QUANTIDADE_ASSUMIDA");
    expect(ALERT_CODE_LABELS.QUANTIDADE_ASSUMIDA).toBe("Quantidade assumida como 1: confira");
  });
});

describe("GRES-01, 02, 04, 05, 09: rótulos do painel da Etapa 4", () => {
  it("os dois níveis da oferta têm nome em português", () => {
    expect(LEVEL_LABELS).toEqual({ GRADUACAO: "Graduação", POS_GRADUACAO: "Pós-graduação" });
  });

  it("os textos do painel são os da spec", () => {
    expect(PANEL_LABELS).toEqual({
      totalWithGroup1: "Grupos I a VIII",
      totalWithoutGroup1: "Grupos II a VIII",
      minimumUndefined: "Mínimo não definido",
      minimumMet: "Atinge o mínimo",
      minimumNotMet: "Não atinge o mínimo",
      awaitingValidation: "Aguardando validação",
      noOffers: "Nenhuma disciplina lançada no Grupo I",
      noAcademicPeriod: "Sem período letivo",
      teaching: "Docência (PIT)",
    });
  });

  it("o texto do mínimo do painel é o mesmo de MINIMUM_LABELS", () => {
    expect(MINIMUM_LABELS.ATINGE).toBe(PANEL_LABELS.minimumMet);
    expect(MINIMUM_LABELS.NAO_ATINGE).toBe(PANEL_LABELS.minimumNotMet);
    expect(MINIMUM_LABELS.NAO_DEFINIDO).toBe(PANEL_LABELS.minimumUndefined);
  });

  it("as barras usam nomes curtos de grupo, um por grupo de I a VIII", () => {
    expect(Object.keys(GROUP_NAMES)).toEqual(["1", "2", "3", "4", "5", "6", "7", "8"]);
    expect(GROUP_NAMES[1]).toBe("Docência");
  });
});

describe("PAR-07..10, DOS-07: tipos, códigos e pendentes da banca", () => {
  it("os cinco códigos novos de recusa existem e têm texto em português", () => {
    for (const code of ["CONCLUSAO_AUSENTE", "BANCA_SEM_MEMBROS", "TABELA_AUSENTE", "TABELA_DESATUALIZADA", "PORTARIA_EXISTENTE"] as const) {
      expect(GENERATION_CODES).toContain(code);
      expect(GENERATION_CODE_LABELS[code], code).toBeTruthy();
    }
  });

  it("PAR-10: TABELA_DESATUALIZADA diz que a pontuação mudou e manda gerar a Tabela de novo", () => {
    expect(GENERATION_CODE_LABELS.TABELA_DESATUALIZADA).toBe(
      "A pontuação mudou depois da última Tabela; gere a Tabela de novo",
    );
  });

  it("os cinco tipos de documento têm nome, e só eles", () => {
    expect([...DOCUMENT_KINDS]).toEqual(["TABELA", "RELATORIO", "COMPROVANTE", "REQUERIMENTO", "PARECER"]);
    expect(Object.keys(DOCUMENT_KIND_LABELS).sort()).toEqual([...DOCUMENT_KINDS].sort());
    expect(DOCUMENT_KIND_LABELS.REQUERIMENTO).toBe("Requerimento");
    expect(DOCUMENT_KIND_LABELS.PARECER).toBe("Parecer");
  });

  it("DOS-07: a conclusão exige só a Tabela, o Relatório e o Comprovante", () => {
    expect([...ARTIFACT_KINDS]).toEqual(["TABELA", "RELATORIO", "COMPROVANTE"]);
  });

  it("DOS-07: cada item pendente da banca tem rótulo, e só eles", () => {
    expect([...PENDING_BOARD_ITEMS]).toEqual(["REQUERIMENTO", "PORTARIA_BANCA", "PARECER"]);
    expect(PENDING_BOARD_LABELS).toEqual({
      REQUERIMENTO: "Requerimento",
      PORTARIA_BANCA: "Portaria da banca",
      PARECER: "Parecer",
    });
  });
});

describe("PORT-02, PORT-03, PORT-07, DOS-02, DOS-03, DOS-05: rótulos da banca e do checklist", () => {
  it("cada função da banca tem rótulo, e só elas", () => {
    expect(Object.keys(BOARD_ROLE_LABELS).sort()).toEqual([...BOARD_ROLES].sort());
    expect(BOARD_ROLE_LABELS).toEqual({ PRESIDENTE: "Presidente", MEMBRO: "Membro", SUPLENTE: "Suplente" });
  });

  it("PORT-05: a origem informada pela pessoa se chama 'informado pela pessoa'", () => {
    expect(Object.keys(VALUE_SOURCE_LABELS).sort()).toEqual([...VALUE_SOURCES].sort());
    expect(VALUE_SOURCE_LABELS.INFORMADO).toBe("informado pela pessoa");
    expect(VALUE_SOURCE_LABELS.EXTRAIDO).toBeTruthy();
  });

  it("cada estado da leitura tem rótulo, e só eles", () => {
    expect(Object.keys(READING_STATE_LABELS).sort()).toEqual([...READING_STATES].sort());
    expect([...READING_STATES]).toEqual(["SEM_ARQUIVO", "PENDENTE", "LENDO", "LIDA", "FALHOU"]);
    for (const state of READING_STATES) expect(READING_STATE_LABELS[state], state).toBeTruthy();
  });

  it("PORT-07: cada motivo da falha da leitura tem texto em português, e só eles", () => {
    expect(Object.keys(READING_CODE_LABELS).sort()).toEqual([...READING_CODES].sort());
    for (const code of READING_CODES) {
      expect(READING_CODE_LABELS[code], code).toMatch(/\s/);
      expect(READING_CODE_LABELS[code], code).not.toMatch(/[A-Z]{3,}_[A-Z]/);
    }
  });

  it("PORT-03: os dois avisos da portaria têm texto, e só eles", () => {
    expect(Object.keys(ORDINANCE_WARNING_LABELS).sort()).toEqual([...ORDINANCE_WARNING_CODES].sort());
    expect([...ORDINANCE_WARNING_CODES].sort()).toEqual(["MEMBROS_NAO_ENCONTRADOS", "VALOR_SEM_ORIGEM"]);
    for (const code of ORDINANCE_WARNING_CODES) expect(ORDINANCE_WARNING_LABELS[code], code).toMatch(/\s/);
  });

  it("DOS-02, DOS-03, DOS-05: o checklist tem Gerado, Registrada, Entregue e Pendente", () => {
    expect(Object.keys(CHECKLIST_STATE_LABELS).sort()).toEqual([...CHECKLIST_STATES].sort());
    expect(CHECKLIST_STATE_LABELS).toEqual({
      GERADO: "Gerado",
      REGISTRADA: "Registrada",
      ENTREGUE: "Entregue",
      PENDENTE: "Pendente",
    });
  });
});

describe("GTAB-34, GTAB-36: motivos de bloqueio, etiquetas e histórico das tabelas", () => {
  it("todo código de motivo tem texto em português sem o código cru, e só eles", () => {
    expect(Object.keys(BLOCK_REASON_LABELS).sort()).toEqual([...BLOCK_REASON_CODES].sort());
    expect([...BLOCK_REASON_CODES].sort()).toEqual(
      [
        "TABELA_ARQUIVADA",
        "TABELA_COM_VERSAO_EM_USO",
        "TABELA_OFICIAL_PROTEGIDA",
        "UNIDADE_COM_VERSAO_EM_USO",
        "ULTIMA_VERSAO_DA_TABELA",
        "VERSAO_EM_USO_DE_UNIDADE",
        "VERSAO_NAO_MAIS_RECENTE",
        "VERSAO_SUBSTITUI_OUTRA",
        "VERSAO_SUBSTITUIDA",
        "VERSAO_USADA_POR_PROCESSO",
      ].sort(),
    );
    for (const code of BLOCK_REASON_CODES) {
      const text = blockReasonText(code, { processCount: 2, acronyms: ["FASI"] });
      expect(text, code).toMatch(/\s/);
      expect(text, code).not.toContain(code);
      expect(text, code).not.toMatch(/[A-Z]{3,}_[A-Z]/);
    }
  });

  it("blockReasonText escreve a quantidade de processos, no singular e no plural", () => {
    expect(blockReasonText("VERSAO_USADA_POR_PROCESSO", { processCount: 1 })).toContain("1 processo");
    expect(blockReasonText("VERSAO_USADA_POR_PROCESSO", { processCount: 1 })).not.toContain("1 processos");
    expect(blockReasonText("VERSAO_USADA_POR_PROCESSO", { processCount: 3 })).toContain("3 processos");
  });

  it("blockReasonText escreve as siglas ordenadas e separadas por vírgula", () => {
    const text = blockReasonText("VERSAO_EM_USO_DE_UNIDADE", { acronyms: ["IFCH", "FASI"] });
    expect(text).toContain("FASI, IFCH");
    expect(blockReasonText("TABELA_COM_VERSAO_EM_USO", { acronyms: ["IFCH", "FASI"] })).toContain("FASI, IFCH");
    expect(blockReasonText("UNIDADE_COM_VERSAO_EM_USO", { acronyms: ["FASI"] })).toContain("FASI");
  });

  it("código desconhecido cai no texto genérico, sem mostrar o código", () => {
    const text = blockReasonText("CODIGO_NOVO_DO_SERVIDOR", {});
    expect(text).toBe("Esta ação não é permitida agora.");
    expect(text).not.toContain("CODIGO_NOVO");
  });

  it("as cinco etiquetas da versão existem", () => {
    expect(TABLE_BADGE_LABELS).toEqual({
      inUse: "Em uso",
      usedByProcess: "Usada por processo",
      superseded: "Substituída",
      archived: "Arquivada",
      ended: "Encerrada",
    });
    expect(inUseBadge("FASI")).toBe("Em uso (FASI)");
  });

  it("cada ação e cada entidade do histórico têm rótulo", () => {
    expect(HISTORY_ACTION_LABELS).toEqual({
      CREATE: "Criação",
      UPDATE: "Alteração",
      ARCHIVE: "Arquivamento",
      DELETE: "Exclusão",
    });
    expect(HISTORY_ENTITY_LABELS).toEqual({
      scoring_table: "Tabela",
      scoring_version: "Versão",
      unit_scoring_default: "Versão em uso da unidade",
    });
  });

  it("as chaves de mudança do histórico viram texto legível", () => {
    expect(historyChangeLabel("archived")).toBe("Arquivada");
    expect(historyChangeLabel("unit_ids")).toBe("Unidades");
    expect(historyChangeLabel("version_id")).toBe("Versão em uso");
    expect(historyChangeLabel("criteria.2.7.unit_points")).toBe("II.7: Pontos por unidade");
    expect(historyChangeLabel("criteria.8.37.max_points")).toBe("VIII.37: Limite de pontos");
    expect(historyChangeLabel("criteria.2.7.description")).toBe("II.7: Descrição");
    expect(historyChangeLabel("chave_nova")).toBe("chave_nova");
  });
});
