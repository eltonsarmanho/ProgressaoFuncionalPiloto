import type { BoardRole, ChecklistState, OrdinanceWarningCode, ReadingCode, ReadingState, ValueSource } from "./api/board";
import type {
  DocumentKind,
  EntrySource,
  GenerationAlert,
  GenerationAlertCode,
  GenerationCode,
  GenerationState,
  PendingBoardItem,
} from "./api/generated";
import type { DocumentStatus, InvalidReason, Level, Modality, NormKind, ProcessStatus, Severity, Validity } from "./api/types";

export const STATUS_LABELS: Record<ProcessStatus, string> = {
  RASCUNHO: "Rascunho",
  EM_ANDAMENTO: "Em andamento",
  CONCLUIDO: "Concluído",
  ARQUIVADO: "Arquivado",
};

export const SEVERITY_LABELS: Record<Severity, string> = {
  ERRO: "Erro",
  ALERTA: "Alerta",
  REQUER_ANALISE_NORMATIVA: "Requer análise normativa",
};

export const SEVERITIES: Severity[] = ["ERRO", "ALERTA", "REQUER_ANALISE_NORMATIVA"];

export const MODALITY_LABELS: Record<Modality, string> = {
  PROGRESSAO: "Progressão",
  PROMOCAO: "Promoção",
};

/** "2024-11-23" -> "23/11/2024" without timezone shifts. */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export const GROUP_NAMES: Record<number, string> = {
  1: "Docência",
  2: "Orientação",
  3: "Bancas",
  4: "Extensão",
  5: "Pesquisa",
  6: "Administrativas e de Representação",
  7: "Capacitação",
  8: "Produção",
};

const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"];
export function roman(n: number): string {
  return ROMAN[n] ?? String(n);
}

export const ROW_STATUS_LABELS: Record<string, string> = {
  PONTUADA: "Pontuada",
  POTENCIAL: "Potencial",
  NAO_PONTUADA: "Não pontuada",
};

export const REASON_LABELS: Record<string, string> = {
  FORA_DO_INTERSTICIO: "Fora do interstício",
  DUPLICIDADE: "Duplicidade",
  SEM_ENQUADRAMENTO: "Sem enquadramento na tabela",
  GRUPO_NAO_CONTA: "Grupo não conta no total",
  SEM_TABELA: "Sem tabela escolhida",
  AGUARDANDO_REVISAO: "Aguardando revisão",
  REJEITADA: "Rejeitada",
  CARGA_HORARIA_INSUFICIENTE: "Carga horária abaixo do mínimo do item",
};

/** Plain-language names for alert codes; codes without an entry are shown as sent by the API. */
export const ALERT_CODE_LABELS: Record<string, string> = {
  CARGA_HORARIA_NAO_INFORMADA: "Carga horária não informada",
  DATA_FIM_AUSENTE: "Sem data final: quantidade limitada aos anos completos até o fim do interstício",
  VALOR_UNITARIO_MANUAL: "Valor unitário informado por você",
  QUANTIDADE_ASSUMIDA: "Quantidade assumida como 1: confira",
  TITULACAO_INSUFICIENTE: "Titulação insuficiente para a classe pretendida",
};

/** NBASE-01: the kinds of norm of the registry. */
export const NORM_KIND_LABELS: Record<NormKind, string> = {
  LEI: "Lei",
  RESOLUCAO: "Resolução",
  INSTRUCAO_NORMATIVA: "Instrução normativa",
  MANUAL: "Manual",
  TABELA: "Tabela",
  OUTRO: "Outro",
};

/** SEC-07: the short name of each reason an activity is not valid (the counts of the section title). */
export const INVALID_REASON_LABELS = {
  REJEITADA: "Rejeitada por você",
  FORA_DO_INTERSTICIO: "Fora do interstício",
  CARGA_HORARIA_INSUFICIENTE: "Carga horária insuficiente",
  GRUPO_NAO_CONTA: "Grupo não conta no total",
  DUPLICIDADE: "Duplicidade",
} satisfies Record<InvalidReason, string>;

/** Hours arrive as text without trailing zeros ("19", "19.5"); pt-BR writes the comma. */
const hoursText = (value: string | undefined) => `${formatDecimal(value)} h`;

/**
 * SEC-07: why an activity is not valid, in words, from `validity.params`. A period (categories
 * measured by year) shows its start and end where a date shows the day.
 */
export function invalidReasonText(validity: Pick<Validity, "reason" | "params">): string {
  const { reason, params } = validity;
  if (reason === "FORA_DO_INTERSTICIO") {
    // A group I offer with neither date nor period of dates is judged by its academic period (GI-09).
    const byAcademicPeriod = !params.event_date && !params.period_start && !params.period_end && params.academic_period;
    const when = params.event_date
      ? `data ${formatDate(params.event_date)}`
      : byAcademicPeriod
        ? `período letivo ${params.academic_period}`
        : `período ${params.period_start ? formatDate(params.period_start) : "—"} a ${params.period_end ? formatDate(params.period_end) : "—"}`;
    const interstice =
      params.interstice_start && params.interstice_end
        ? `; interstício ${formatDate(params.interstice_start)} a ${formatDate(params.interstice_end)}`
        : "";
    return `${INVALID_REASON_LABELS.FORA_DO_INTERSTICIO}: ${when}${interstice}`;
  }
  if (reason === "CARGA_HORARIA_INSUFICIENTE") {
    return `${INVALID_REASON_LABELS.CARGA_HORARIA_INSUFICIENTE}: ${hoursText(params.hours)}; o item exige ${hoursText(params.min_hours)}`;
  }
  return reason ? INVALID_REASON_LABELS[reason] : "";
}

/** SEC-04: the seals of a valid activity; the text is always there, never only a colour. */
export const BADGE_NEEDS_CATEGORY = "Precisa de categoria";
export const BADGE_AWAITING_VALIDATION = "Aguardando validação";
export const BADGE_VALIDATED = "Validada";

/** SEC-05: why the way to Etapa 4 is closed. */
export function needsCategoryMessage(count: number): string {
  return count === 1 ? "1 atividade precisa de categoria" : `${count} atividades precisam de categoria`;
}

export const MINIMUM_LABELS: Record<string, string> = {
  ATINGE: "Atinge o mínimo",
  NAO_ATINGE: "Não atinge o mínimo",
  NAO_DEFINIDO: "Mínimo não definido",
};

/** NLIST-01: the kinds of rule that cite a norm. */
export const LINKED_RULE_LABELS: Record<string, string> = {
  CARREIRA: "Estrutura de carreira",
  TABELA: "Tabela de pontuação",
  TITULACAO: "Titulação",
};

/** NMIN-02: why the minimum of the new career structure is not defined. */
export const MINIMUM_UNDEFINED_REASON =
  "Mínimo não definido: a Res. 4.644/2015, art. 12, fixa mínimos só para as classes da estrutura antiga";

/** GRES-04: the level of a group I offer. */
export const LEVEL_LABELS: Record<Level, string> = {
  GRADUACAO: "Graduação",
  POS_GRADUACAO: "Pós-graduação",
};

/** The texts of the scoring panel of Etapa 4 (GRES-01..09). */
export const PANEL_LABELS = {
  totalWithGroup1: "Grupos I a VIII",
  totalWithoutGroup1: "Grupos II a VIII",
  minimumUndefined: MINIMUM_LABELS.NAO_DEFINIDO,
  minimumMet: MINIMUM_LABELS.ATINGE,
  minimumNotMet: MINIMUM_LABELS.NAO_ATINGE,
  awaitingValidation: BADGE_AWAITING_VALIDATION,
  noOffers: "Nenhuma disciplina lançada no Grupo I",
  noAcademicPeriod: "Sem período letivo",
  teaching: "Docência (PIT)",
} as const;

export const TABLE_STATUS_LABELS: Record<string, string> = {
  OFICIAL: "Oficial",
  PENDENTE_VALIDACAO: "Pendente de validação",
};

/** "414.00" -> "414,00" (pt-BR); null/undefined -> "—". */
export function formatDecimal(value: string | null | undefined): string {
  if (value == null || value === "") return "—";
  return value.replace(".", ",");
}

/* ---- Documentos (Etapa 2) ---- */

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  PENDENTE: "Pendente",
  PROCESSANDO: "Processando",
  PROCESSADO: "Processado",
  REQUER_REVISAO: "Requer revisão",
  EXTRAIDO_SEM_IA: "Extraído sem IA",
  FALHOU: "Falhou",
};

/** Statuses in which the worker still owns the document: the page keeps polling (TELA-03). */
export const ACTIVE_DOCUMENT_STATUSES: DocumentStatus[] = ["PENDENTE", "PROCESSANDO"];

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  DECLARACAO_BANCA: "Declaração de banca",
  DECLARACAO_ORIENTACAO: "Declaração de orientação",
  DECLARACAO_DISCIPLINAS: "Declaração de disciplinas",
  ATA_DEFESA: "Ata de defesa",
  CERTIFICADO: "Certificado",
  PORTARIA: "Portaria",
  ARTIGO: "Artigo",
  REGISTRO_SOFTWARE: "Registro de software",
  OUTRO: "Outro",
};

/** Why a document is in its status; codes without an entry are shown as sent by the API. */
export const DOCUMENT_CODE_LABELS: Record<string, string> = {
  SEM_ITEM_DE_PONTUACAO: "Sem item de pontuação",
  TEXTO_ILEGIVEL: "Texto ilegível",
  DOCENTE_DIVERGENTE: "O nome do docente no documento não confere",
  RESPOSTA_INVALIDA: "A IA devolveu uma resposta inválida",
  NAO_ENCONTRADO_NO_TEXTO: "Valor não encontrado no texto da página",
  TRUNCADO: "Resposta da IA cortada",
  NENHUMA_ATIVIDADE_ENCONTRADA: "Nenhuma atividade encontrada",
  IA_CREDENCIAL_RECUSADA: "A credencial da IA foi recusada",
  IA_INDISPONIVEL: "IA indisponível",
  TEMPO_ESGOTADO: "Tempo de leitura esgotado",
  QUANTIDADE_ESTIMADA: "Quantidade estimada: confira",
  ATIVIDADE_REPETIDA: "Atividade repetida no documento: criada uma só vez",
  CLAUSULA_DE_DISPENSA: "Dispensa da função: não vira atividade",
  TENTATIVAS_ESGOTADAS: "Tentativas de leitura esgotadas: reprocesse o documento",
  DATA_PARCIAL: "Data só com mês e ano: confira o período",
  DATA_FIM_DERIVADA: "Data final calculada do prazo da portaria: confira",
  DATA_FIM_AUSENTE: "Sem data final na portaria: quantidade estimada até o fim do interstício",
  INDEXACAO_NAO_COMPROVADA: "Indexação do periódico não comprovada no texto: item de artigo não indexado, confira",
  ENQUADRADO_COMO_CAPACITACAO:
    "Certificado de participação com carga horária: enquadrado como curso de curta duração (VII.10) pelo sistema, confira",
  DOCUMENTO_FORA_DO_INTERSTICIO: "Documento fora do interstício: não será processado nas próximas etapas",
  ERRO_INTERNO: "Erro interno",
};

export const NO_ITEM_CODE = "SEM_ITEM_DE_PONTUACAO";
export const OUTSIDE_INTERSTICE_CODE = "DOCUMENTO_FORA_DO_INTERSTICIO";

/** "2024-11-23" -> "23/11/2024"; with month precision "2022-03-01" -> "03/2022". */
export function formatDocumentDate(iso: string, precision: "DAY" | "MONTH" | null | undefined): string {
  const [y, m] = iso.split("-");
  return precision === "MONTH" ? `${m}/${y}` : formatDate(iso);
}

/** FORA-02: the warning of a document outside the interstice; null when the API sent no dates. */
export function outsideIntersticeWarning(doc: {
  document_date?: string | null;
  document_date_precision?: "DAY" | "MONTH" | null;
  interstice_start?: string | null;
  interstice_end?: string | null;
}): string | null {
  if (!doc.document_date || !doc.interstice_start || !doc.interstice_end) return null;
  const when = formatDocumentDate(doc.document_date, doc.document_date_precision);
  return `Data do documento ${when}, fora do interstício (${formatDate(doc.interstice_start)} a ${formatDate(doc.interstice_end)}): não será processado nas próximas etapas`;
}

export const TAXONOMY_LABELS: Record<string, string> = {
  DISCIPLINA_MINISTRADA: "Disciplina ministrada",
  ORIENTACAO_POS_DOUTORADO: "Tutoria de pós-doutorado",
  ORIENTACAO_DOUTORADO: "Orientação de doutorado",
  COORIENTACAO_DOUTORADO: "Coorientação de doutorado",
  ORIENTACAO_MESTRADO: "Orientação de mestrado",
  COORIENTACAO_MESTRADO: "Coorientação de mestrado",
  ORIENTACAO_ESPECIALIZACAO: "Orientação de especialização",
  ORIENTACAO_TCC_GRADUACAO: "Orientação de TCC de graduação",
  COORIENTACAO_TCC_GRADUACAO: "Coorientação de TCC de graduação",
  ORIENTACAO_EM_ANDAMENTO_DOUTORADO: "Orientação de doutorado em andamento",
  ORIENTACAO_EM_ANDAMENTO_MESTRADO: "Orientação de mestrado em andamento",
  ORIENTACAO_EM_ANDAMENTO_TCC: "Orientação de TCC em andamento",
  ORIENTACAO_PROJETO_INSTITUCIONAL: "Orientação em projeto institucional",
  ORIENTACAO_ESTAGIO: "Orientação de estágio",
  ORIENTACAO_MONITORIA: "Orientação de monitoria",
  BANCA_DOUTORADO: "Banca de doutorado",
  BANCA_MESTRADO: "Banca de mestrado",
  BANCA_ESPECIALIZACAO: "Banca de especialização",
  BANCA_TCC_GRADUACAO: "Banca de TCC de graduação",
  BANCA_CONCURSO_SUBSTITUTO: "Banca de concurso para professor substituto",
  BANCA_CONCURSO_EFETIVO: "Banca de concurso para professor efetivo",
  BANCA_QUALIFICACAO: "Banca de qualificação",
  BANCA_SELECAO_POS: "Banca de seleção de pós-graduação",
  BANCA_SELECAO_BOLSAS: "Banca de seleção de bolsas",
  BANCA_PROCESSO_SELETIVO: "Banca de processo seletivo",
  EXTENSAO_PROJETO_COORDENACAO: "Coordenação de projeto de extensão",
  EXTENSAO_PROJETO_PARTICIPACAO: "Participação em projeto de extensão",
  EXTENSAO_CURSO_COORDENACAO: "Coordenação de curso de extensão",
  EXTENSAO_CURSO_MINISTRANTE: "Ministrante de curso de extensão",
  EXTENSAO_EVENTO_COORDENACAO: "Coordenação de evento de extensão",
  EXTENSAO_EVENTO_MINISTRANTE: "Ministrante em evento de extensão",
  PESQUISA_PROJETO_COORDENACAO: "Coordenação de projeto de pesquisa",
  PESQUISA_GRUPO_COORDENACAO: "Coordenação de grupo de pesquisa",
  PESQUISA_GRUPO_MEMBRO: "Membro de grupo de pesquisa",
  PESQUISA_BOLSA_PRODUTIVIDADE: "Bolsa de produtividade em pesquisa",
  FUNCAO_DIRETOR_FACULDADE: "Direção de faculdade",
  FUNCAO_VICE_DIRETOR_FACULDADE: "Vice-direção de faculdade",
  FUNCAO_COORDENADOR_CURSO_GRADUACAO: "Coordenação de curso de graduação",
  COMISSAO_ADMINISTRACAO_SUPERIOR: "Comissão da administração superior",
  COMISSAO_NDE_MEMBRO: "Membro de NDE",
  COMISSAO_UNIDADE: "Comissão da unidade",
  COLEGIADO_MEMBRO: "Membro de colegiado",
  CURSO_ESPECIALIZACAO_CONCLUIDO: "Curso de especialização concluído",
  CURSO_APERFEICOAMENTO_CONCLUIDO: "Curso de aperfeiçoamento concluído",
  CURSO_EXTENSAO_CONCLUIDO: "Curso de extensão concluído",
  CURSO_CONCLUIDO: "Curso concluído",
  PARTICIPACAO_EVENTO: "Participação em evento",
  TREINAMENTO_INTERNO: "Treinamento interno",
  ESTAGIO_CAPACITACAO: "Estágio de capacitação",
  LIVRO_COM_PARECERISTAS: "Livro com pareceristas",
  LIVRO_SEM_PARECERISTAS: "Livro sem pareceristas",
  CAPITULO_INTERNACIONAL: "Capítulo de livro internacional",
  CAPITULO_NACIONAL: "Capítulo de livro nacional",
  ARTIGO_INTERNACIONAL_INDEXADO: "Artigo internacional indexado",
  ARTIGO_NACIONAL_INDEXADO: "Artigo nacional indexado",
  ARTIGO_NAO_INDEXADO: "Artigo não indexado",
  TRABALHO_COMPLETO_CONGRESSO: "Trabalho completo em congresso",
  COMUNICACAO_COM_RESUMO: "Comunicação com resumo",
  COMUNICACAO_SEM_RESUMO: "Comunicação sem resumo",
  APRESENTACAO_TRABALHO_INTERNACIONAL: "Apresentação de trabalho internacional",
  APRESENTACAO_TRABALHO_NACIONAL: "Apresentação de trabalho nacional",
  PALESTRA: "Palestra, conferência ou mesa-redonda",
  PATENTE_DEPOSITADA: "Patente depositada",
  PATENTE_CONCEDIDA: "Patente concedida",
  REGISTRO_SOFTWARE: "Registro de software",
  CONSULTORIA_AD_HOC: "Consultoria ad hoc",
  OUTRA: "Outra atividade",
};

/** Below this the extraction is flagged for a closer look (EXT-12). */
export const LOW_CONFIDENCE = 0.7;

/** 3_400_000 -> "3,2 MB"; below 1 MB in KB. */
export function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export const ACTIVITY_STATUS_LABELS: Record<string, string> = {
  AGUARDANDO_REVISAO: "Aguardando revisão",
  VALIDADA: "Validada",
  REJEITADA: "Rejeitada",
};

export const ACTIVITY_SOURCE_LABELS: Record<string, string> = {
  MANUAL: "Cadastrada por você",
  SUGERIDA_IA: "Sugerido pela IA",
  IMPORTADA: "Importada",
};

export const TEXT_METHOD_LABELS: Record<string, string> = {
  TEXTO: "TEXTO (camada de texto do arquivo)",
  OCR: "OCR (leitura da imagem)",
};

/** "IV.3" for an activity item; "Sem enquadramento" when the activity has none. */
export function itemLabel(group: number | null, item: number | null): string {
  if (group == null) return "Sem enquadramento";
  return item == null ? roman(group) : `${roman(group)}.${item}`;
}

/* ---- Documentos gerados (Etapa 5) ---- */

export const GENERATION_STATE_LABELS: Record<GenerationState, string> = {
  GERANDO: "Gerando",
  PRONTO: "Pronto",
  FALHOU: "Falhou",
};

/** Refusals (422, 409, 410) and failures of a generation or a wording; one text for each code. */
export const GENERATION_CODE_LABELS: Record<GenerationCode, string> = {
  SEM_ATIVIDADES_VALIDADAS: "O processo não tem atividade validada. Valide ao menos uma na Etapa 3.",
  TABELA_NAO_ESCOLHIDA: "Escolha a tabela de pontuação na Etapa 4 antes de gerar.",
  ATIVIDADE_SEM_DESCRICAO: "Há atividade validada sem título e sem descrição. Preencha-a na Etapa 3.",
  ATIVIDADE_SEM_CATEGORIA: "Há atividades sem categoria na Etapa 3. Escolha a categoria de cada uma.",
  COMPROVANTE_GRANDE_DEMAIS: "O Comprovante passa de 400 páginas ou de 60 MB. Tire páginas do arranjo.",
  IMAGEM_GRANDE_DEMAIS: "Há imagem PNG acima de 12 megapixels entre os documentos. Envie-a de novo como JPEG ou menor.",
  ORIGINAL_INDISPONIVEL: "Um documento de origem não está mais disponível ou a página não existe mais.",
  ORIGINAIS_EXCLUIDOS: "Os documentos de entrada foram excluídos: o Comprovante não pode mais ser gerado.",
  INTERROMPIDA: "O servidor reiniciou durante o trabalho. Peça de novo.",
  ESPACO_INSUFICIENTE: "Não há espaço livre suficiente no servidor para gerar o documento.",
  ERRO_INTERNO: "Erro interno do servidor. Tente de novo.",
  GERACAO_EM_ANDAMENTO: "Já há uma geração deste documento em andamento.",
  REDACAO_EM_ANDAMENTO: "Já há uma redação desta seção em andamento.",
  ARTEFATOS_PENDENTES: "Gere a Tabela, o Relatório e o Comprovante antes de concluir o processo.",
  CONFIRMACAO_OBRIGATORIA: "Confirme a exclusão dos documentos de entrada para concluir.",
  OPERACAO_EM_ANDAMENTO: "Há geração, redação ou leitura de documento em andamento. Espere terminar.",
  CONCLUSAO_EXIGE_EXCLUSAO: "O processo só é concluído pela conclusão que exclui os documentos de entrada.",
  ARQUIVO_EXCLUIDO: "O arquivo deste documento foi excluído na conclusão do processo.",
  PAGINA_FORA_DO_DOCUMENTO: "A página indicada não existe no documento.",
  VERSAO_DESATUALIZADA: "Os dados mudaram desde que você abriu a tela. A versão atual foi recarregada.",
  PROCESSO_SOMENTE_LEITURA: "O processo está concluído ou arquivado e não aceita alterações.",
  CONCLUSAO_AUSENTE: "Escolha a conclusão do Parecer, Favorável ou Desfavorável, e salve antes de gerar.",
  BANCA_SEM_MEMBROS: "Registre ao menos um membro da banca antes de gerar o Parecer.",
  TABELA_AUSENTE: "Gere a Tabela de Pontuação na Etapa 5 antes de gerar o Parecer.",
  TABELA_DESATUALIZADA: "A pontuação mudou depois da última Tabela; gere a Tabela de novo",
  PORTARIA_EXISTENTE: "Já há uma portaria da banca neste processo. Confirme a substituição para enviar outra.",
};

/** Alerts that travel with a result: the text the block of a document lists. */
export const GENERATION_ALERT_LABELS: Record<GenerationAlertCode, string> = {
  ATIVIDADE_SEM_COMPROVANTE: "Atividade sem comprovante anexado",
  REDACAO_REJEITADA: "A redação da IA trazia dado que não está na atividade e foi recusada: ficou o texto-modelo",
  REDACAO_INDISPONIVEL: "A IA não está disponível agora: ficou o texto-modelo",
  ARRANJO_DESATUALIZADO: "O arranjo do Comprovante está desatualizado: as atividades mudaram depois que ele foi salvo",
  NUMERACAO_DIVERGENTE: "A numeração do Comprovante mudou desde a última versão gerada: gere os dois de novo",
  ATIVIDADES_FORA_DO_DOCUMENTO: "Há atividades que ficaram fora do documento",
  PAGINA_REPETIDA_JUSTIFICADA: "Página repetida com justificativa",
  PAGINA_RASTERIZADA: "Página convertida em imagem para manter o que se vê",
  RASCUNHO_DESATUALIZADO: "O rascunho do Relatório está desatualizado: há atividades novas ou removidas",
  EXCLUSAO_PARCIAL: "Nem todos os arquivos foram excluídos: tente de novo",
};

/** The seal of an entry of the report: who wrote the text that is there now (REL-07). */
export const ENTRY_SOURCE_LABELS: Record<EntrySource, string> = {
  MODELO: "Texto-modelo",
  IA: "Redigido pela IA",
  USUARIO: "Editado",
};

/** Why the check of a wording refused the text of the AI; `REDACAO_REJEITADA` carries them in its message. */
export const WORDING_REASON_LABELS: Record<string, string> = {
  NUMERO: "número que não está na atividade",
  DATA: "data que não está na atividade",
  NOME: "nome que não está na atividade",
  VOCABULARIO: "palavras fora do vocabulário permitido",
  COMPRIMENTO: "texto longo demais",
  PALAVRA_PROIBIDA: "palavra proibida",
};

/** The text of an alert of a draft or a generation: its label, plus the reasons of a refused wording. */
export function alertText(alert: GenerationAlert): string {
  const label = GENERATION_ALERT_LABELS[alert.code] ?? alert.code;
  if (alert.code !== "REDACAO_REJEITADA" || !alert.message) return label;
  const reasons = alert.message.split(",").map((r) => WORDING_REASON_LABELS[r.trim()] ?? r.trim());
  return `${label} (${reasons.join(", ")})`;
}

/**
 * What an alert says beyond its label, or "" when there is nothing to add: the refused wording already
 * carries its reasons in the label, and the left-out count starts by repeating the label.
 */
export function alertDetail(alert: GenerationAlert): string {
  if (alert.code === "REDACAO_REJEITADA") return "";
  const message = alert.message ?? "";
  if (alert.code === "ATIVIDADES_FORA_DO_DOCUMENTO") return message.replace(/^Atividades fora do documento:\s*/i, "");
  return message;
}

/** "20000" -> "20 000": the counter of a text uses a non-breaking space. */
export function formatCount(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/** The documents the system generates: three in the Etapa 5, the Parecer in the Etapa 6 and the Requerimento in the Etapa 7. */
export const DOCUMENT_KIND_LABELS: Record<DocumentKind, string> = {
  TABELA: "Tabela de Pontuação",
  RELATORIO: "Relatório de Atividades",
  COMPROVANTE: "Comprovante de Documentos",
  REQUERIMENTO: "Requerimento",
  PARECER: "Parecer",
};

/** DOS-07: the board documents the conclusion warns are still missing. */
export const PENDING_BOARD_LABELS: Record<PendingBoardItem, string> = {
  REQUERIMENTO: "Requerimento",
  PORTARIA_BANCA: "Portaria da banca",
  PARECER: "Parecer",
};

/** An instant of the server (ISO, UTC) as the day it was in the browser's time zone: "18/11/2026". */
export function formatDay(iso: string): string {
  const when = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(when.getDate())}/${pad(when.getMonth() + 1)}/${when.getFullYear()}`;
}

/* ---- Banca e dossiê (Etapas 6 e 7) ---- */

export const BOARD_ROLE_LABELS: Record<BoardRole, string> = {
  PRESIDENTE: "Presidente",
  MEMBRO: "Membro",
  SUPLENTE: "Suplente",
};

/** PORT-05: where a value of the ordinance came from; the page of an extracted one is shown beside it. */
export const VALUE_SOURCE_LABELS: Record<ValueSource, string> = {
  EXTRAIDO: "lido da portaria",
  INFORMADO: "informado pela pessoa",
};

export const READING_STATE_LABELS: Record<ReadingState, string> = {
  SEM_ARQUIVO: "Sem arquivo",
  PENDENTE: "Na fila de leitura",
  LENDO: "Lendo a portaria",
  LIDA: "Portaria lida",
  FALHOU: "A leitura falhou",
};

/** PORT-07: why a reading failed. */
export const READING_CODE_LABELS: Record<ReadingCode, string> = {
  IA_INDISPONIVEL: "A IA não está disponível agora.",
  IA_CREDENCIAL_RECUSADA: "A credencial da IA foi recusada.",
  RESPOSTA_INVALIDA: "A IA devolveu uma resposta inválida.",
  TEXTO_ILEGIVEL: "Não foi possível ler o texto do arquivo.",
  INTERROMPIDA: "O servidor reiniciou durante a leitura.",
  ERRO_INTERNO: "Erro interno do servidor.",
};

/** PORT-03: the warnings of a reading. */
export const ORDINANCE_WARNING_LABELS: Record<OrdinanceWarningCode, string> = {
  VALOR_SEM_ORIGEM: "O valor não aparece no texto da página citada: confira e digite",
  MEMBROS_NAO_ENCONTRADOS: "Nenhum membro foi encontrado na portaria: digite os membros",
};

/** DOS-02, DOS-03, DOS-05: the state of an item of the checklist of the dossier. */
export const CHECKLIST_STATE_LABELS: Record<ChecklistState, string> = {
  GERADO: "Gerado",
  REGISTRADA: "Registrada",
  ENTREGUE: "Entregue",
  PENDENTE: "Pendente",
};
