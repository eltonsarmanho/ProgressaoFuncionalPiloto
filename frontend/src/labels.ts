import type { Modality, ProcessStatus, Severity } from "./api/types";

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
