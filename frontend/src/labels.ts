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
