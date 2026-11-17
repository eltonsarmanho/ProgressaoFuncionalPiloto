import type { DocumentStatus, Modality, ProcessStatus, Severity } from "./api/types";

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
};

export const MINIMUM_LABELS: Record<string, string> = {
  ATINGE: "Atinge o mínimo",
  NAO_ATINGE: "Não atinge o mínimo",
  NAO_DEFINIDO: "Mínimo não definido",
};

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
  ERRO_INTERNO: "Erro interno",
};

export const NO_ITEM_CODE = "SEM_ITEM_DE_PONTUACAO";

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
